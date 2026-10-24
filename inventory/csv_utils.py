import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import FoodItem


REQUIRED_COLUMNS = ['name', 'quantity', 'expiry_date']

VALID_CATEGORIES = {c[0].lower(): c[0] for c in FoodItem.CATEGORY_CHOICES}
VALID_UNITS = {u[0].lower(): u[0] for u in FoodItem.UNIT_CHOICES}

DATE_FORMATS = [
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%d/%m/%Y',
    '%m/%d/%Y',
    '%Y/%m/%d',
]


def normalize_header(header):
    """Normalize column header names to lowercase standard names."""
    if not header:
        return ''
    cleaned = header.strip().lower().replace(' ', '_').replace('-', '_')
    mapping = {
        'food_name': 'name',
        'item_name': 'name',
        'food': 'name',
        'item': 'name',
        'qty': 'quantity',
        'amount': 'quantity',
        'unit_of_measure': 'unit',
        'uom': 'unit',
        'units': 'unit',
        'expiration_date': 'expiry_date',
        'exp_date': 'expiry_date',
        'expiry': 'expiry_date',
        'expiration': 'expiry_date',
        'desc': 'description',
        'food_description': 'description',
        'donor': 'donor_info',
        'provider': 'donor_info',
        'supplier': 'donor_info',
        'batch': 'batch_number',
        'batch_no': 'batch_number',
        'lot': 'batch_number',
        'lot_number': 'batch_number',
        'location': 'storage_location',
        'storage': 'storage_location',
    }
    return mapping.get(cleaned, cleaned)


def parse_date(date_str):
    """Attempt parsing date with multiple common formats."""
    cleaned = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD or DD-MM-YYYY.")


def process_csv_file(uploaded_file, user=None):
    """
    Safely parses an uploaded CSV file, validates rows, and persists valid items.
    Security rules:
      - Authenticated user is always enforced as added_by (owner).
      - Never trusts owner/role IDs from CSV content.
      - Uses safe standard parsing with zero execution of contents.
      - Enforces atomic transaction per batch or isolates row failures.
    Returns:
        dict: {
            'success_count': int,
            'failed_count': int,
            'errors': list of dicts [{'row': N, 'errors': [...]}]
        }
    """
    errors = []
    created_items = []

    try:
        raw_data = uploaded_file.read()
        # Decode trying utf-8-sig first (handles Excel UTF-8 BOM), then utf-8, fallback to latin-1
        try:
            decoded_file = raw_data.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                decoded_file = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                decoded_file = raw_data.decode('latin-1')

        io_string = io.StringIO(decoded_file)
        sample = decoded_file[:2048]
        delimiter = ','
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ','

        io_string.seek(0)
        reader = csv.reader(io_string, delimiter=delimiter)

        try:
            raw_headers = next(reader)
        except StopIteration:
            return {
                'success_count': 0,
                'failed_count': 1,
                'errors': [{'row': 1, 'errors': ['Uploaded CSV file is completely empty.']}],
            }

        headers = [normalize_header(h) for h in raw_headers]

        # Verify required headers exist
        missing_headers = [req for req in REQUIRED_COLUMNS if req not in headers]
        if missing_headers:
            return {
                'success_count': 0,
                'failed_count': 1,
                'errors': [{
                    'row': 1,
                    'errors': [f"Missing required columns in CSV header: {', '.join(missing_headers)}. Found: {', '.join(raw_headers)}"]
                }],
            }

        header_index_map = {col: idx for idx, col in enumerate(headers)}

        # Row-by-row validation & transactional creation
        row_number = 1
        with transaction.atomic():
            for row in reader:
                row_number += 1

                # Skip completely empty lines
                if not row or not any(cell.strip() for cell in row):
                    continue

                row_errors = []

                def get_val(col_name):
                    idx = header_index_map.get(col_name)
                    if idx is not None and idx < len(row):
                        return row[idx].strip()
                    return ''

                name = get_val('name')
                category_raw = get_val('category')
                quantity_raw = get_val('quantity')
                unit_raw = get_val('unit')
                expiry_date_raw = get_val('expiry_date')
                description = get_val('description')
                donor_info = get_val('donor_info')
                batch_number = get_val('batch_number')
                storage_location = get_val('storage_location')

                # Fallback donor info to user's organization name if blank
                if not donor_info and user and hasattr(user, 'profile') and user.profile.organization_name:
                    donor_info = user.profile.organization_name

                # Validation: Name
                if not name:
                    row_errors.append("Food name is required.")

                # Validation: Quantity
                quantity = None
                if not quantity_raw:
                    row_errors.append("Quantity is required.")
                else:
                    try:
                        quantity = Decimal(quantity_raw)
                        if quantity <= Decimal('0'):
                            row_errors.append(f"Quantity must be greater than zero (found: '{quantity_raw}').")
                    except (InvalidOperation, ValueError):
                        row_errors.append(f"Invalid numeric quantity: '{quantity_raw}'.")

                # Validation: Expiry Date
                expiry_date = None
                if not expiry_date_raw:
                    row_errors.append("Expiry date is required.")
                else:
                    try:
                        expiry_date = parse_date(expiry_date_raw)
                    except ValueError as ve:
                        row_errors.append(str(ve))

                # Normalize Category
                category = 'Other'
                if category_raw:
                    norm_cat = category_raw.lower()
                    if norm_cat in VALID_CATEGORIES:
                        category = VALID_CATEGORIES[norm_cat]
                    else:
                        matched = False
                        for key, val in VALID_CATEGORIES.items():
                            if key in norm_cat or norm_cat in key:
                                category = val
                                matched = True
                                break
                        if not matched:
                            category = 'Other'

                # Normalize Unit
                unit = 'units'
                if unit_raw:
                    norm_unit = unit_raw.lower()
                    if norm_unit in VALID_UNITS:
                        unit = VALID_UNITS[norm_unit]
                    else:
                        unit = 'units'

                if row_errors:
                    errors.append({'row': row_number, 'errors': row_errors, 'data': name or f'Row {row_number}'})
                    continue

                food_item = FoodItem(
                    name=name,
                    category=category,
                    quantity=quantity,
                    unit=unit,
                    description=description,
                    expiry_date=expiry_date,
                    batch_number=batch_number,
                    storage_location=storage_location,
                    donor_info=donor_info,
                    added_by=user if (user and user.is_authenticated) else None,
                )

                try:
                    food_item.full_clean()
                    food_item.save()
                    created_items.append(food_item)
                except ValidationError as ve:
                    err_messages = []
                    if hasattr(ve, 'message_dict'):
                        for f, msgs in ve.message_dict.items():
                            err_messages.append(f"{f}: {', '.join(msgs)}")
                    else:
                        err_messages.extend(ve.messages)
                    errors.append({'row': row_number, 'errors': err_messages, 'data': name})
                except Exception as e:
                    errors.append({'row': row_number, 'errors': [f"Database error: {str(e)}"], 'data': name})

    except Exception as e:
        errors.append({'row': 0, 'errors': [f"Failed to process CSV file: {str(e)}"], 'data': 'File parsing'})

    return {
        'success_count': len(created_items),
        'failed_count': len(errors),
        'errors': errors,
    }
