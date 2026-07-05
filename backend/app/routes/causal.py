import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.causal_model import CausalModel, ECONOMIC_FACTORS
from app.models.activity import Activity

logger = logging.getLogger(__name__)

causal_bp = Blueprint('causal', __name__)


@causal_bp.route('/graphs', methods=['GET'])
@jwt_required()
def get_causal_graphs():
    """Get all causal graphs for current user"""
    current_user_id = get_jwt_identity()
    models = CausalModel.query.filter_by(user_id=current_user_id).all()
    
    return jsonify({
        'causal_graphs': [m.to_dict() for m in models]
    }), 200


@causal_bp.route('/graphs', methods=['POST'])
@jwt_required()
def create_causal_graph():
    """Create a new causal graph"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Graph name is required'}), 400
    
    model = CausalModel(
        user_id=current_user_id,
        name=name,
        description=data.get('description'),
        dag_structure=data.get('dag_structure', {'nodes': [], 'edges': []}),
        treatment_effects=data.get('treatment_effects', {}),
        confidence_scores=data.get('confidence_scores', {}),
        sector_sensitivity=data.get('sector_sensitivity', {})
    )
    
    db.session.add(model)
    db.session.commit()
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='causal_analysis',
        title=f'Created causal graph: {name}',
        entity_type='causal_model',
        entity_id=model.id
    )
    
    return jsonify({
        'message': 'Causal graph created successfully',
        'causal_graph': model.to_dict()
    }), 201


@causal_bp.route('/graphs/<int:graph_id>', methods=['GET'])
@jwt_required()
def get_causal_graph(graph_id):
    """Get a specific causal graph"""
    current_user_id = get_jwt_identity()
    model = CausalModel.query.filter_by(id=graph_id, user_id=current_user_id).first()
    
    if not model:
        return jsonify({'error': 'Causal graph not found'}), 404
    
    return jsonify({
        'causal_graph': model.to_dict()
    }), 200


@causal_bp.route('/graphs/<int:graph_id>', methods=['PUT'])
@jwt_required()
def update_causal_graph(graph_id):
    """Update a causal graph"""
    current_user_id = get_jwt_identity()
    model = CausalModel.query.filter_by(id=graph_id, user_id=current_user_id).first()
    
    if not model:
        return jsonify({'error': 'Causal graph not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        model.name = data['name']
    if 'description' in data:
        model.description = data['description']
    if 'dag_structure' in data:
        model.dag_structure = data['dag_structure']
    if 'treatment_effects' in data:
        model.treatment_effects = data['treatment_effects']
    if 'confidence_scores' in data:
        model.confidence_scores = data['confidence_scores']
    if 'sector_sensitivity' in data:
        model.sector_sensitivity = data['sector_sensitivity']
    if 'is_validated' in data:
        model.is_validated = data['is_validated']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Causal graph updated successfully',
        'causal_graph': model.to_dict()
    }), 200


@causal_bp.route('/graphs/<int:graph_id>', methods=['DELETE'])
@jwt_required()
def delete_causal_graph(graph_id):
    """Delete a causal graph"""
    current_user_id = get_jwt_identity()
    model = CausalModel.query.filter_by(id=graph_id, user_id=current_user_id).first()
    
    if not model:
        return jsonify({'error': 'Causal graph not found'}), 404
    
    model_name = model.name
    db.session.delete(model)
    db.session.commit()
    
    return jsonify({
        'message': f'Causal graph "{model_name}" deleted successfully'
    }), 200


@causal_bp.route('/estimate-effects', methods=['POST'])
@jwt_required()
def estimate_treatment_effects():
    """Estimate causal treatment effects"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    treatment = data.get('treatment')  # e.g., 'interest_rates'
    outcome = data.get('outcome')  # e.g., 'tech_returns'
    dag_structure = data.get('dag_structure')
    treatment_value = data.get('treatment_value', 1.0)  # Magnitude of what-if change
    
    if not treatment or not outcome:
        return jsonify({'error': 'Treatment and outcome are required'}), 400
    
    # Run causal effect estimation
    from app.services.causal_service import estimate_causal_effect
    result = estimate_causal_effect(treatment, outcome, dag_structure)
    
    # Scale the ATE by treatment_value so what-if slider has real effect
    if result and 'ate' in result and treatment_value != 1.0:
        result['ate'] = result['ate'] * treatment_value
        result['treatment_value'] = treatment_value
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='causal_analysis',
        title=f'Estimated effect: {treatment} → {outcome}',
        activity_metadata={'result': result}
    )
    
    return jsonify(result), 200


@causal_bp.route('/sensitivity-matrix', methods=['GET'])
@jwt_required(optional=True)
def get_sensitivity_matrix():
    """Get sector sensitivity matrix to economic factors
    
    Works for both authenticated and unauthenticated users.
    Returns ML-trained matrix for authenticated users if available.
    """
    from app.services.causal_service import get_sector_sensitivity_matrix
    
    current_user_id = get_jwt_identity()
    matrix = get_sector_sensitivity_matrix(user_id=current_user_id)
    
    return jsonify({
        'sensitivity_matrix': matrix
    }), 200


@causal_bp.route('/validate-dag', methods=['POST'])
@jwt_required()
def validate_dag():
    """Validate a DAG structure"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    dag_structure = data.get('dag_structure')
    
    if not dag_structure:
        return jsonify({'error': 'DAG structure is required'}), 400
    
    from app.services.causal_service import validate_dag_structure
    validation_result = validate_dag_structure(dag_structure)
    
    return jsonify(validation_result), 200


@causal_bp.route('/economic-factors', methods=['GET'])
def get_economic_factors():
    """Get available economic factors for causal analysis"""
    return jsonify({
        'economic_factors': ECONOMIC_FACTORS
    }), 200


@causal_bp.route('/discover', methods=['POST'])
@jwt_required(optional=True)
def discover_causal_relationships():
    """Discover causal relationships using various methods (Granger, PC, LiNGAM, etc.)"""
    data = request.get_json() or {}
    method = data.get('method', 'granger')
    sectors = data.get('sectors', ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY'])
    significance = data.get('significance', 0.05)

    try:
        from app.services.causal_discovery import CausalDiscoveryEngine
        from app.services.data_pipeline import DataPipeline
        import os

        DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
        pipeline = DataPipeline()

        # Real market data from the local price store (never synthetic noise)
        import numpy as np
        import pandas as pd
        from app.services.price_store import get_price_store

        store = get_price_store()
        prices = store.get_history(sectors + ['SPY', '^VIX', '^TNX'], start='2018-01-01')
        available = [s for s in sectors if s in prices.columns]
        if prices.empty or not available:
            return jsonify({
                'method': method, 'sectors': sectors, 'relationships': {},
                'status': 'error',
                'note': 'Market data unavailable for causal discovery'
            }), 503

        sector_df = prices[available].pct_change().dropna()
        macro_df = pd.DataFrame(index=sector_df.index)
        if 'SPY' in prices.columns:
            macro_df['market_return'] = prices['SPY'].pct_change().reindex(sector_df.index)
        if '^VIX' in prices.columns:
            macro_df['vix_change'] = prices['^VIX'].pct_change().reindex(sector_df.index)
        if '^TNX' in prices.columns:
            macro_df['yield_change'] = prices['^TNX'].diff().reindex(sector_df.index)
        macro_df = macro_df.dropna()
        common = sector_df.index.intersection(macro_df.index)
        sector_df, macro_df = sector_df.loc[common], macro_df.loc[common]

        engine = CausalDiscoveryEngine()
        relationships = engine.discover_all_relationships(sector_df, macro_df)

        return jsonify({
            'method': method,
            'sectors': sectors,
            'relationships': relationships,
            'status': 'success'
        }), 200
    except Exception as e:
        logger.error(f"Causal discovery failed: {e}")
        return jsonify({
            'method': method,
            'sectors': sectors,
            'relationships': {},
            'status': 'fallback',
            'note': 'Returning empty relationships due to data unavailability'
        }), 200


@causal_bp.route('/treatment-effect', methods=['POST'])
@jwt_required(optional=True)
def estimate_treatment_effect_alias():
    """Alias for /estimate-effects — estimate causal treatment effect"""
    return estimate_treatment_effects()


@causal_bp.route('/dag', methods=['GET'])
@jwt_required(optional=True)
def get_dag():
    """Get the current causal DAG structure"""
    try:
        from app.services.causal_discovery import CausalDiscoveryEngine
        engine = CausalDiscoveryEngine()
        dag = engine.build_causal_dag()
        return jsonify({'dag': dag, 'status': 'success'}), 200
    except Exception as e:
        return jsonify({'dag': {'nodes': [], 'edges': []}, 'status': 'fallback'}), 200


@causal_bp.route('/what-if', methods=['POST'])
@jwt_required(optional=True)
def what_if_analysis():
    """What-if scenario analysis for a single causal variable"""
    data = request.get_json() or {}
    variable = data.get('variable', 'interest_rate')
    change = data.get('change', 0.25)
    target_sectors = data.get('target_sectors', ['XLK', 'XLF'])

    try:
        from app.services.causal_service import get_active_sensitivity_matrix
        matrix = get_active_sensitivity_matrix()

        results = {}
        for sector_key, sensitivities in matrix.items():
            sensitivity = sensitivities.get(variable, sensitivities.get('interest_rates', 0))
            results[sector_key] = round(sensitivity * change * 100, 2)

        return jsonify({
            'variable': variable,
            'change': change,
            'estimated_impacts': results,
            'target_sectors': target_sectors
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
