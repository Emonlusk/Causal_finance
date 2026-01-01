from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.scenario import Scenario, PRESET_SCENARIOS
from app.models.activity import Activity

scenarios_bp = Blueprint('scenarios', __name__)


@scenarios_bp.route('/', methods=['GET'])
@jwt_required(optional=True)
def get_scenarios():
    """Get all scenarios for current user
    
    Returns user's scenarios if authenticated, empty list otherwise.
    """
    current_user_id = get_jwt_identity()
    
    if current_user_id:
        scenarios = Scenario.query.filter_by(user_id=current_user_id).order_by(Scenario.created_at.desc()).all()
        return jsonify({
            'scenarios': [s.to_dict() for s in scenarios]
        }), 200
    else:
        # Return empty list for unauthenticated users
        return jsonify({
            'scenarios': []
        }), 200


@scenarios_bp.route('/', methods=['POST'])
@jwt_required()
def create_scenario():
    """Create and optionally run a scenario"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Scenario name is required'}), 400
    
    scenario = Scenario(
        user_id=current_user_id,
        name=name,
        description=data.get('description'),
        scenario_type=data.get('scenario_type', 'custom'),
        parameters=data.get('parameters', {}),
        portfolio_id=data.get('portfolio_id')
    )
    
    db.session.add(scenario)
    db.session.commit()
    
    return jsonify({
        'message': 'Scenario created successfully',
        'scenario': scenario.to_dict()
    }), 201


@scenarios_bp.route('/<int:scenario_id>', methods=['GET'])
@jwt_required()
def get_scenario(scenario_id):
    """Get a specific scenario"""
    current_user_id = get_jwt_identity()
    scenario = Scenario.query.filter_by(id=scenario_id, user_id=current_user_id).first()
    
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    return jsonify({
        'scenario': scenario.to_dict()
    }), 200


@scenarios_bp.route('/<int:scenario_id>', methods=['DELETE'])
@jwt_required()
def delete_scenario(scenario_id):
    """Delete a scenario"""
    current_user_id = get_jwt_identity()
    scenario = Scenario.query.filter_by(id=scenario_id, user_id=current_user_id).first()
    
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    scenario_name = scenario.name
    db.session.delete(scenario)
    db.session.commit()
    
    return jsonify({
        'message': f'Scenario "{scenario_name}" deleted successfully'
    }), 200


@scenarios_bp.route('/run', methods=['POST'])
@jwt_required()
def run_scenario():
    """Run a scenario simulation"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    parameters = data.get('parameters', {})
    portfolio_weights = data.get('portfolio_weights')
    save_results = data.get('save_results', False)
    scenario_name = data.get('name', 'Unnamed Scenario')
    
    if not parameters:
        return jsonify({'error': 'Scenario parameters are required'}), 400
    
    # Run simulation
    from app.services.scenario_service import run_scenario_simulation
    results = run_scenario_simulation(parameters, portfolio_weights)
    
    # Save scenario if requested
    scenario = None
    if save_results:
        scenario = Scenario(
            user_id=current_user_id,
            name=scenario_name,
            scenario_type='custom',
            parameters=parameters,
            results=results,
            run_at=datetime.utcnow()
        )
        db.session.add(scenario)
        db.session.commit()
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='scenario_run',
        title=f'Ran scenario: {scenario_name}',
        description=f'Impact: {results.get("portfolio_impact", 0):.1%}',
        entity_type='scenario' if scenario else None,
        entity_id=scenario.id if scenario else None,
        metadata={'parameters': parameters}
    )
    
    response = {
        'results': results
    }
    
    if scenario:
        response['scenario'] = scenario.to_dict()
    
    return jsonify(response), 200


@scenarios_bp.route('/presets', methods=['GET'])
def get_preset_scenarios():
    """Get available preset scenarios"""
    return jsonify({
        'presets': PRESET_SCENARIOS
    }), 200


@scenarios_bp.route('/presets/<preset_id>/run', methods=['POST'])
@jwt_required()
def run_preset_scenario(preset_id):
    """Run a preset scenario"""
    current_user_id = get_jwt_identity()
    
    if preset_id not in PRESET_SCENARIOS:
        return jsonify({'error': 'Preset scenario not found'}), 404
    
    preset = PRESET_SCENARIOS[preset_id]
    data = request.get_json() or {}
    portfolio_weights = data.get('portfolio_weights')
    
    # Run simulation with preset parameters
    from app.services.scenario_service import run_scenario_simulation
    results = run_scenario_simulation(preset['parameters'], portfolio_weights)
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='scenario_run',
        title=f'Ran preset: {preset["name"]}',
        description=preset['description'],
        metadata={'preset_id': preset_id, 'parameters': preset['parameters']}
    )
    
    return jsonify({
        'preset': preset,
        'results': results
    }), 200


@scenarios_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_scenarios():
    """Compare multiple scenarios"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    scenario_params_list = data.get('scenarios', [])
    portfolio_weights = data.get('portfolio_weights')
    
    if not scenario_params_list:
        return jsonify({'error': 'At least one scenario is required'}), 400
    
    from app.services.scenario_service import run_scenario_simulation
    
    comparisons = []
    for params in scenario_params_list:
        results = run_scenario_simulation(params.get('parameters', {}), portfolio_weights)
        comparisons.append({
            'name': params.get('name', 'Unnamed'),
            'parameters': params.get('parameters', {}),
            'results': results
        })
    
    return jsonify({
        'comparisons': comparisons
    }), 200
