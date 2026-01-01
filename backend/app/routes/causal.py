from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.causal_model import CausalModel, ECONOMIC_FACTORS
from app.models.activity import Activity

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
    
    if not treatment or not outcome:
        return jsonify({'error': 'Treatment and outcome are required'}), 400
    
    # Run causal effect estimation
    from app.services.causal_service import estimate_causal_effect
    result = estimate_causal_effect(treatment, outcome, dag_structure)
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='causal_analysis',
        title=f'Estimated effect: {treatment} → {outcome}',
        metadata={'result': result}
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
