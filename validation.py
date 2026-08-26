import pandas as pd
import numpy as np
from typing import Dict, Union

def validate_and_predict(
    model,
    transaction_data: Union[pd.DataFrame, pd.Series, dict],
    required_features: list = None,
) -> Dict:
    """
    Safely predict fraud probability with comprehensive input validation.

    Returns a dict with:
      - 'status': 'success' | 'flagged_for_review'
      - 'fraud_prob': float (0-1) if success, None if flagged
      - 'reason': None if success, str explaining the failure otherwise
      - 'details': dict with diagnostic info

    Production behavior: any validation failure → human review, no silent fallback.
    """

    # Expected features for this model
    if required_features is None:
        required_features = ['Time', 'Amount'] + [f'V{i}' for i in range(1, 29)]

    # Normalize input to DataFrame
    if isinstance(transaction_data, dict):
        transaction_df = pd.DataFrame([transaction_data])
    elif isinstance(transaction_data, pd.Series):
        transaction_df = transaction_data.to_frame().T
    elif isinstance(transaction_data, pd.DataFrame):
        transaction_df = transaction_data.copy()
    else:
        return {
            'status': 'flagged_for_review',
            'fraud_prob': None,
            'reason': 'invalid_input_type',
            'details': {'error': f'Expected DataFrame/Series/dict, got {type(transaction_data).__name__}'}
        }

    # Validation checks (fail-fast on first issue)

    # Check 1: Missing columns
    missing_cols = set(required_features) - set(transaction_df.columns)
    if missing_cols:
        return {
            'status': 'flagged_for_review',
            'fraud_prob': None,
            'reason': 'missing_features',
            'details': {'missing': sorted(missing_cols)}
        }

    # Check 2: Null values
    null_cols = transaction_df[required_features].columns[transaction_df[required_features].isnull().any()].tolist()
    if null_cols:
        return {
            'status': 'flagged_for_review',
            'fraud_prob': None,
            'reason': 'null_values',
            'details': {'null_columns': null_cols}
        }

    # Check 3: Type validation (all features should be numeric)
    non_numeric = []
    for col in required_features:
        if not pd.api.types.is_numeric_dtype(transaction_df[col]):
            non_numeric.append(col)
    if non_numeric:
        return {
            'status': 'flagged_for_review',
            'fraud_prob': None,
            'reason': 'non_numeric_features',
            'details': {'non_numeric_columns': non_numeric}
        }

    # Check 4: Range validation (domain-specific constraints)
    range_violations = []

    # Time: should be non-negative (seconds since first transaction)
    if (transaction_df['Time'] < 0).any():
        range_violations.append({'feature': 'Time', 'constraint': 'must be >= 0'})

    # Amount: should be non-negative (can't have negative payment amounts)
    if (transaction_df['Amount'] < 0).any():
        range_violations.append({'feature': 'Amount', 'constraint': 'must be >= 0'})

    # V1-V28: flag extreme outliers (>50 in absolute value)
    for col in [f'V{i}' for i in range(1, 29)]:
        if (transaction_df[col].abs() > 50).any():
            range_violations.append({'feature': col, 'constraint': 'abs value > 50 (extreme outlier)'})

    if range_violations:
        return {
            'status': 'flagged_for_review',
            'fraud_prob': None,
            'reason': 'range_violations',
            'details': {'violations': range_violations}
        }

    # Check 5: Infinity / NaN after all conversions
    if not np.isfinite(transaction_df[required_features].values).all():
        return {
            'status': 'flagged_for_review',
            'fraud_prob': None,
            'reason': 'non_finite_values',
            'details': {'error': 'Contains inf or NaN after type coercion'}
        }

    # All checks passed — safe to predict
    try:
        fraud_prob = model.predict_proba(transaction_df[required_features])[0, 1]
        return {
            'status': 'success',
            'fraud_prob': float(fraud_prob),
            'reason': None,
            'details': {'validated': True}
        }
    except Exception as e:
        # Model-level failure (shouldn't happen if validation passed, but catch it anyway)
        return {
            'status': 'flagged_for_review',
            'fraud_prob': None,
            'reason': 'model_error',
            'details': {'error': str(e)}
        }
