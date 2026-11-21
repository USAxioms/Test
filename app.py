"""
app.py - The Production Backend Shell
Runs the Pharmaceutical Superintelligence engine on Render.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import hashlib
from datetime import datetime
import traceback

# Import the core engine
from phar import PharmaceuticalSuperintelligence, TherapeuticTarget, PharmaceuticalAxiomRegistry

app = Flask(__name__)
# Allow the front end to communicate with this backend
CORS(app)

# Initialize the engine globally
print("⚡ Booting Pharmaceutical Superintelligence Engine...")
ENGINE = PharmaceuticalSuperintelligence()
print("✓ Engine ready.")

# In-memory ledger for the session
SESSION_LEDGER = []

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_ledger_entry(prompt: str, result_dict: dict) -> dict:
    """Creates a cryptographic proof of the transaction."""
    entry_id = len(SESSION_LEDGER)
    parent_hash = SESSION_LEDGER[-1]["hash"] if SESSION_LEDGER else "GENESIS"
    
    entry = {
        "entry_id": entry_id,
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "result": result_dict,
        "parent_hash": parent_hash
    }
    
    # Compute SHA-256 hash of the entry
    entry_string = json.dumps(entry, sort_keys=True)
    entry["hash"] = hashlib.sha256(entry_string.encode()).hexdigest()
    
    SESSION_LEDGER.append(entry)
    return entry

# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health():
    """Health check to verify the engine is running."""
    return jsonify({
        "status": "operational",
        "engine": "Pharmaceutical Superintelligence v1.0",
        "ledger_entries": len(SESSION_LEDGER)
    })

@app.route('/axioms', methods=['GET'])
def get_axioms():
    """Returns the 6 foundational pharmaceutical axioms."""
    axioms = PharmaceuticalAxiomRegistry.get_foundational_axioms()
    return jsonify([
        {
            "name": ax.name,
            "statement": ax.statement,
            "certainty": ax.certainty,
            "nuclear_charge": ax.nuclear_charge
        } for ax in axioms
    ])

@app.route('/discover', methods=['POST'])
def discover():
    """
    Main endpoint: Receives a target, runs the discovery,
    records to the ledger, and returns the verified result.
    """
    try:
        data = request.json
        if not data or 'target_name' not in data:
            return jsonify({"error": "Missing target_name in payload"}), 400

        # 1. Reconstruct the Target from the Front End Payload
        target = TherapeuticTarget(
            target_id=data.get('target_id', 'TARGET_001'),
            target_name=data['target_name'],
            target_class=data.get('target_class', 'unknown'),
            disease=data.get('disease', 'unknown'),
            disease_prevalence=data.get('disease_prevalence', 1.0),
            validation_score=data.get('validation_score', 0.9),
            druggability_score=data.get('druggability_score', 0.8),
            clinical_evidence=data.get('clinical_evidence', []),
            known_modulators=data.get('known_modulators', []),
            market_size_usd=data.get('market_size_usd', 1000.0),
            unmet_need_score=data.get('unmet_need_score', 0.9)
        )

        constraints = data.get('constraints', {})

        # 2. Run the Engine
        print(f"⚡ Running discovery for: {target.target_name}")
        drug_candidate = ENGINE.discover_drug_candidate(target, constraints)
        
        # 3. Extract the latest reasoning pathway for the ledger
        latest_pathway_id = list(ENGINE.reasoning_pathways.keys())[-1]
        pathway = ENGINE.reasoning_pathways[latest_pathway_id]

        # 4. Build the Result Payload
        result_dict = {
            "compound_id": drug_candidate.compound_id,
            "target": drug_candidate.target,
            "smiles": drug_candidate.smiles,
            "molecular_weight": drug_candidate.molecular_weight,
            "logp": drug_candidate.logp,
            "lipinski_compliant": drug_candidate.satisfies_lipinski(),
            "predicted_kd_nM": drug_candidate.predicted_kd,
            "predicted_efficacy": drug_candidate.predicted_efficacy,
            "safety_index": drug_candidate.predicted_safety_index,
            "adme_profile": drug_candidate.adme_profile,
            "pathway_strength": pathway.pathway_strength,
            "emergence_metric": pathway.emergence_metric,
            "axioms_used": list(pathway.axioms_used)
        }

        # 5. Record to Ledger
        ledger_entry = create_ledger_entry(
            prompt=f"Discover drug for {target.target_name}",
            result_dict=result_dict
        )

        # 6. Send Response to Front End
        return jsonify({
            "status": "success",
            "result": result_dict,
            "ledger_proof": {
                "entry_id": ledger_entry["entry_id"],
                "hash": ledger_entry["hash"],
                "parent_hash": ledger_entry["parent_hash"]
            }
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/ledger', methods=['GET'])
def get_ledger():
    """Returns the full ledger history."""
    return jsonify(SESSION_LEDGER)

@app.route('/verify_ledger', methods=['GET'])
def verify_ledger():
    """Verifies the cryptographic integrity of the ledger chain."""
    if not SESSION_LEDGER:
        return jsonify({"status": "empty", "valid": True})

    for i in range(1, len(SESSION_LEDGER)):
        current = SESSION_LEDGER[i]
        previous = SESSION_LEDGER[i-1]
        
        # Check parent link
        if current["parent_hash"] != previous["hash"]:
            return jsonify({"valid": False, "error": f"Broken chain at entry {i}"}), 400
            
        # Re-compute hash to check for tampering
        entry_copy = current.copy()
        stored_hash = entry_copy.pop("hash")
        entry_string = json.dumps(entry_copy, sort_keys=True)
        computed_hash = hashlib.sha256(entry_string.encode()).hexdigest()
        
        if stored_hash != computed_hash:
            return jsonify({"valid": False, "error": f"Tampered hash at entry {i}"}), 400

    return jsonify({"valid": True, "entries_verified": len(SESSION_LEDGER)})

if __name__ == '__main__':
    # Render uses gunicorn in production. This is for local testing.
    app.run(host='0.0.0.0', port=10000)
