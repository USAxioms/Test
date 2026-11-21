"""
app.py - Minimal Backend Shell
Single-file engine wrapper for Render.
"""

from flask import Flask, request, jsonify
import json
import hashlib
from datetime import datetime

# Import the engine
from phar import PharmaceuticalSuperintelligence, TherapeuticTarget

app = Flask(__name__)

# Initialize engine once
ENGINE = PharmaceuticalSuperintelligence()

# In-memory ledger
LEDGER = []

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "operational", "entries": len(LEDGER)})

@app.route('/discover', methods=['POST'])
def discover():
    try:
        data = request.json
        
        # 1. Build the target from the payload
        target = TherapeuticTarget(
            target_id=data.get('target_id', 'TARGET_001'),
            target_name=data.get('target_name', 'Unknown'),
            target_class=data.get('target_class', 'unknown'),
            disease=data.get('disease', 'unknown'),
            disease_prevalence=data.get('prevalence', 1.0),
            validation_score=data.get('validation', 0.9),
            druggability_score=data.get('druggability', 0.8),
            clinical_evidence=[],
            known_modulators=[],
            market_size_usd=data.get('market_size', 1000.0),
            unmet_need_score=data.get('unmet_need', 0.9)
        )
        
        # 2. Run the engine
        candidate = ENGINE.discover_drug_candidate(target, {})
        
        # 3. Build the result
        result = {
            "compound_id": candidate.compound_id,
            "target": candidate.target,
            "efficacy": candidate.predicted_efficacy,
            "safety_index": candidate.predicted_safety_index,
            "lipinski": candidate.satisfies_lipinski(),
            "lambda_total": ENGINE.r3_processor.metrics_history[-1].capability_score if ENGINE.r3_processor.metrics_history else 0.0
        }
        
        # 4. Record to ledger
        entry = {
            "id": len(LEDGER),
            "timestamp": datetime.now().isoformat(),
            "target": target.target_name,
            "result": result,
            "parent": LEDGER[-1]["hash"] if LEDGER else "GENESIS"
        }
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        LEDGER.append(entry)
        
        # 5. Return
        return jsonify({
            "status": "success",
            "result": result,
            "proof": entry["hash"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
