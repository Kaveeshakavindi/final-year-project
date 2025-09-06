import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from neo4j import GraphDatabase
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ESG Risk Categories
class ESGCategory(Enum):
    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"
    GOVERNANCE = "governance"

class RiskLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ESGRiskScore:
    category: ESGCategory
    risk_level: RiskLevel
    score: float
    confidence: float
    reasoning: List[str]

# 1. Neo4j Knowledge Graph Interface
class SupplyChainKnowledgeGraph:
    """Interface to Neo4j knowledge graph containing supply chain data"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def get_supplier_info(self, supplier_id: str) -> Dict:
        """Get comprehensive supplier information"""
        with self.driver.session() as session:
            query = """
            MATCH (s:Supplier {id: $supplier_id})
            OPTIONAL MATCH (s)-[:LOCATED_IN]->(c:Country)
            OPTIONAL MATCH (s)-[:HAS_CERTIFICATION]->(cert:Certification)
            OPTIONAL MATCH (s)-[:REPORTED_INCIDENT]->(inc:Incident)
            OPTIONAL MATCH (s)-[:SUPPLIES_TO]->(comp:Company)
            RETURN s, c, collect(cert) as certifications, 
                   collect(inc) as incidents, collect(comp) as customers
            """
            result = session.run(query, supplier_id=supplier_id)
            return result.single()
    
    def get_supply_chain_path(self, start_supplier: str, end_company: str) -> List[Dict]:
        """Get supply chain path between entities"""
        with self.driver.session() as session:
            query = """
            MATCH path = shortestPath((start:Supplier {id: $start_supplier})
                      -[:SUPPLIES_TO*]-(end:Company {id: $end_company}))
            RETURN nodes(path) as supply_chain
            """
            result = session.run(query, start_supplier=start_supplier, end_company=end_company)
            return [record["supply_chain"] for record in result]
    
    def get_esg_events(self, supplier_id: str, days_back: int = 365) -> List[Dict]:
        """Get ESG-related events for a supplier"""
        with self.driver.session() as session:
            query = """
            MATCH (s:Supplier {id: $supplier_id})-[:INVOLVED_IN]->(e:ESGEvent)
            WHERE e.date >= date() - duration({days: $days_back})
            RETURN e
            ORDER BY e.date DESC
            """
            result = session.run(query, supplier_id=supplier_id, days_back=days_back)
            return [record["e"] for record in result]
    
    def get_supplier_network(self, supplier_id: str, depth: int = 2) -> Dict:
        """Get supplier's network (sub-suppliers, partners, etc.)"""
        with self.driver.session() as session:
            query = """
            MATCH (s:Supplier {id: $supplier_id})
            CALL apoc.path.subgraphAll(s, {
                relationshipFilter: "SUPPLIES_TO|PARTNERS_WITH|SUB_SUPPLIER",
                maxLevel: $depth
            })
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
            result = session.run(query, supplier_id=supplier_id, depth=depth)
            return result.single()

# 2. Neural Risk Prediction Models
class ESGRiskPredictor(nn.Module):
    """Neural network for predicting ESG risks from supplier features"""
    
    def __init__(self, input_dim: int, hidden_dims: List[int] = [128, 64, 32]):
        super(ESGRiskPredictor, self).__init__()
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.BatchNorm1d(hidden_dim)
            ])
            prev_dim = hidden_dim
        
        # Output layers for each ESG category
        self.feature_extractor = nn.Sequential(*layers)
        self.environmental_head = nn.Linear(prev_dim, 4)  # 4 risk levels
        self.social_head = nn.Linear(prev_dim, 4)
        self.governance_head = nn.Linear(prev_dim, 4)
        
        # Confidence estimation
        self.confidence_head = nn.Linear(prev_dim, 3)  # Confidence for each category
        
    def forward(self, x):
        features = self.feature_extractor(x)
        
        env_risk = torch.softmax(self.environmental_head(features), dim=1)
        social_risk = torch.softmax(self.social_head(features), dim=1)
        gov_risk = torch.softmax(self.governance_head(features), dim=1)
        confidence = torch.sigmoid(self.confidence_head(features))
        
        return {
            'environmental': env_risk,
            'social': social_risk,
            'governance': gov_risk,
            'confidence': confidence
        }

class TimeSeriesRiskAnalyzer(nn.Module):
    """LSTM-based model for analyzing temporal ESG risk patterns"""
    
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2):
        super(TimeSeriesRiskAnalyzer, self).__init__()
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=8, batch_first=True)
        self.risk_classifier = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 12)  # 3 categories × 4 risk levels
        )
        
    def forward(self, x):
        # x: (batch, sequence_length, features)
        lstm_out, _ = self.lstm(x)
        
        # Apply attention to focus on important time periods
        attn_out, attn_weights = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Use last timestep for prediction
        risk_scores = self.risk_classifier(attn_out[:, -1, :])
        
        return risk_scores.view(-1, 3, 4), attn_weights

# 3. Feature Engineering from Knowledge Graph
class SupplyChainFeatureExtractor:
    """Extract neural network features from Neo4j knowledge graph"""
    
    def __init__(self, kg: SupplyChainKnowledgeGraph):
        self.kg = kg
    
    def extract_supplier_features(self, supplier_id: str) -> np.ndarray:
        """Extract comprehensive features for a supplier"""
        supplier_info = self.kg.get_supplier_info(supplier_id)
        network_info = self.kg.get_supplier_network(supplier_id)
        esg_events = self.kg.get_esg_events(supplier_id)
        
        features = []
        
        # Basic supplier features
        supplier = supplier_info['s']
        features.extend(self._encode_supplier_basics(supplier))
        
        # Geographic features
        country = supplier_info['c']
        features.extend(self._encode_geographic_risk(country))
        
        # Certification features
        certifications = supplier_info['certifications']
        features.extend(self._encode_certifications(certifications))
        
        # Historical incident features
        incidents = supplier_info['incidents']
        features.extend(self._encode_incident_history(incidents))
        
        # Network features
        features.extend(self._encode_network_features(network_info))
        
        # ESG event features
        features.extend(self._encode_esg_events(esg_events))
        
        return np.array(features, dtype=np.float32)
    
    def _encode_supplier_basics(self, supplier) -> List[float]:
        """Encode basic supplier information"""
        features = []
        
        # Company size (employees)
        employees = supplier.get('employees', 0)
        features.append(np.log1p(employees))
        
        # Revenue
        revenue = supplier.get('annual_revenue', 0)
        features.append(np.log1p(revenue))
        
        # Years in operation
        founded_year = supplier.get('founded_year', 2020)
        years_operation = 2024 - founded_year
        features.append(years_operation / 100.0)  # Normalize
        
        # Industry sector (one-hot encoded top sectors)
        sector = supplier.get('sector', 'other')
        sectors = ['manufacturing', 'textiles', 'electronics', 'automotive', 'other']
        features.extend([1.0 if sector == s else 0.0 for s in sectors])
        
        return features
    
    def _encode_geographic_risk(self, country) -> List[float]:
        """Encode country-based ESG risk factors"""
        if not country:
            return [0.0] * 10
        
        features = []
        
        # ESG risk indices (normalized 0-1)
        features.append(country.get('corruption_index', 50) / 100.0)
        features.append(country.get('environmental_performance_index', 50) / 100.0)
        features.append(country.get('labor_rights_index', 50) / 100.0)
        features.append(country.get('political_stability_index', 50) / 100.0)
        
        # Economic indicators
        features.append(country.get('gdp_per_capita', 10000) / 100000.0)
        features.append(country.get('regulatory_quality', 50) / 100.0)
        
        # Climate risk factors
        features.append(country.get('climate_vulnerability', 50) / 100.0)
        features.append(country.get('water_stress_level', 50) / 100.0)
        features.append(country.get('deforestation_rate', 1) / 10.0)
        features.append(country.get('carbon_intensity', 500) / 1000.0)
        
        return features
    
    def _encode_certifications(self, certifications) -> List[float]:
        """Encode supplier certifications"""
        cert_types = ['ISO14001', 'ISO45001', 'SA8000', 'FSC', 'BSCI', 'SEDEX']
        features = []
        
        cert_names = [cert.get('name', '') for cert in certifications]
        
        for cert_type in cert_types:
            has_cert = 1.0 if any(cert_type in name for name in cert_names) else 0.0
            features.append(has_cert)
        
        # Certification recency score
        if certifications:
            most_recent = max(cert.get('issue_date', '2000-01-01') for cert in certifications)
            days_since = (datetime.now() - datetime.fromisoformat(most_recent)).days
            recency_score = max(0, 1 - days_since / 1095)  # 3 years max
        else:
            recency_score = 0.0
        
        features.append(recency_score)
        
        return features
    
    def _encode_incident_history(self, incidents) -> List[float]:
        """Encode historical ESG incidents"""
        features = []
        
        # Count incidents by category
        env_incidents = sum(1 for inc in incidents if inc.get('category') == 'environmental')
        social_incidents = sum(1 for inc in incidents if inc.get('category') == 'social')
        gov_incidents = sum(1 for inc in incidents if inc.get('category') == 'governance')
        
        # Normalize by log
        features.extend([np.log1p(env_incidents), np.log1p(social_incidents), np.log1p(gov_incidents)])
        
        # Recent incident severity
        recent_incidents = [inc for inc in incidents 
                          if (datetime.now() - datetime.fromisoformat(inc.get('date', '2000-01-01'))).days <= 365]
        
        if recent_incidents:
            avg_severity = np.mean([inc.get('severity', 1) for inc in recent_incidents])
            features.append(avg_severity / 10.0)  # Normalize to 0-1
        else:
            features.append(0.0)
        
        return features
    
    def _encode_network_features(self, network_info) -> List[float]:
        """Encode supplier network characteristics"""
        if not network_info or not network_info.get('nodes'):
            return [0.0] * 8
        
        nodes = network_info['nodes']
        relationships = network_info.get('relationships', [])
        
        features = []
        
        # Network size
        features.append(np.log1p(len(nodes)))
        features.append(np.log1p(len(relationships)))
        
        # Network diversity (different node types)
        node_types = set(node.get('labels', ['Unknown'])[0] for node in nodes)
        features.append(len(node_types) / 10.0)  # Normalize
        
        # High-risk country exposure
        high_risk_countries = ['Country1', 'Country2']  # Define based on your data
        high_risk_exposure = sum(1 for node in nodes 
                               if node.get('labels', [''])[0] == 'Country' and 
                               node.get('name', '') in high_risk_countries)
        features.append(high_risk_exposure / max(1, len(nodes)))
        
        # Supplier tier distribution
        tier1_count = sum(1 for node in nodes if node.get('tier') == 1)
        tier2_count = sum(1 for node in nodes if node.get('tier') == 2)
        tier3_plus = len(nodes) - tier1_count - tier2_count
        
        total_suppliers = max(1, len(nodes))
        features.extend([tier1_count/total_suppliers, tier2_count/total_suppliers, 
                        tier3_plus/total_suppliers])
        
        return features
    
    def _encode_esg_events(self, esg_events) -> List[float]:
        """Encode recent ESG events"""
        features = []
        
        # Event counts by category
        env_events = sum(1 for event in esg_events if event.get('category') == 'environmental')
        social_events = sum(1 for event in esg_events if event.get('category') == 'social')
        gov_events = sum(1 for event in esg_events if event.get('category') == 'governance')
        
        features.extend([np.log1p(env_events), np.log1p(social_events), np.log1p(gov_events)])
        
        # Recent trend (last 90 days vs previous 90 days)
        now = datetime.now()
        recent_events = [e for e in esg_events 
                        if (now - datetime.fromisoformat(e.get('date', '2000-01-01'))).days <= 90]
        older_events = [e for e in esg_events 
                       if 90 < (now - datetime.fromisoformat(e.get('date', '2000-01-01'))).days <= 180]
        
        trend_score = len(recent_events) - len(older_events)
        features.append(trend_score / 10.0)  # Normalize
        
        # Average impact score
        if esg_events:
            avg_impact = np.mean([event.get('impact_score', 0) for event in esg_events])
            features.append(avg_impact / 10.0)  # Normalize
        else:
            features.append(0.0)
        
        return features

# 4. Symbolic Reasoning Engine
class ESGRuleEngine:
    """Symbolic reasoning for ESG risk assessment"""
    
    def __init__(self):
        self.rules = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize with standard ESG risk rules"""
        
        # Environmental rules
        self.add_rule("high_carbon_intensity", "environmental_risk_high", 0.8)
        self.add_rule("no_environmental_certification", "environmental_risk_medium", 0.6)
        self.add_rule("recent_environmental_incident", "environmental_risk_critical", 0.9)
        self.add_rule("high_water_stress_location", "environmental_risk_high", 0.7)
        
        # Social rules
        self.add_rule("high_labor_rights_risk_country", "social_risk_high", 0.8)
        self.add_rule("no_social_certification", "social_risk_medium", 0.5)
        self.add_rule("recent_labor_incident", "social_risk_critical", 0.95)
        self.add_rule("child_labor_risk_sector", "social_risk_high", 0.85)
        
        # Governance rules
        self.add_rule("high_corruption_country", "governance_risk_high", 0.8)
        self.add_rule("no_governance_policies", "governance_risk_medium", 0.6)
        self.add_rule("recent_governance_incident", "governance_risk_critical", 0.9)
        self.add_rule("poor_transparency_score", "governance_risk_high", 0.7)
        
        # Cross-category rules
        self.add_rule("multiple_high_risks", "overall_risk_critical", 0.9)
        self.add_rule("tier3_supplier_with_incidents", "supply_chain_risk_high", 0.8)
    
    def add_rule(self, condition: str, conclusion: str, confidence: float):
        """Add a reasoning rule"""
        self.rules.append({
            'condition': condition,
            'conclusion': conclusion,
            'confidence': confidence
        })
    
    def evaluate_facts(self, facts: Dict[str, float]) -> Dict[str, Tuple[float, List[str]]]:
        """Evaluate rules against given facts"""
        conclusions = {}
        
        for rule in self.rules:
            condition = rule['condition']
            conclusion = rule['conclusion']
            confidence = rule['confidence']
            
            # Check if condition is met (simple threshold-based for now)
            if condition in facts and facts[condition] > 0.5:
                if conclusion not in conclusions:
                    conclusions[conclusion] = (0.0, [])
                
                # Update confidence using maximum
                current_conf, reasoning = conclusions[conclusion]
                new_conf = max(current_conf, confidence * facts[condition])
                reasoning.append(f"Rule: {condition} -> {conclusion} (conf: {confidence:.2f})")
                
                conclusions[conclusion] = (new_conf, reasoning)
        
        return conclusions

# 5. Main Neuro-Symbolic ESG System
class NeuroSymbolicESGSystem:
    """Complete neuro-symbolic system for ESG risk analysis"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        # Initialize components
        self.kg = SupplyChainKnowledgeGraph(neo4j_uri, neo4j_user, neo4j_password)
        self.feature_extractor = SupplyChainFeatureExtractor(self.kg)
        self.rule_engine = ESGRuleEngine()
        
        # Neural models (will be loaded from trained weights)
        self.risk_predictor = None
        self.time_series_analyzer = None
        
        logger.info("Neuro-Symbolic ESG System initialized")
    
    def initialize_neural_models(self, feature_dim: int):
        """Initialize neural models with proper dimensions"""
        self.risk_predictor = ESGRiskPredictor(feature_dim)
        self.time_series_analyzer = TimeSeriesRiskAnalyzer(feature_dim)
        
        # Load pre-trained weights if available
        # self.risk_predictor.load_state_dict(torch.load('esg_risk_model.pth'))
    
    def analyze_supplier_risk(self, supplier_id: str) -> Dict[str, ESGRiskScore]:
        """Complete ESG risk analysis for a supplier"""
        logger.info(f"Analyzing ESG risk for supplier: {supplier_id}")
        
        # Step 1: Extract features from knowledge graph
        features = self.feature_extractor.extract_supplier_features(supplier_id)
        
        # Initialize models if not done
        if self.risk_predictor is None:
            self.initialize_neural_models(len(features))
        
        # Step 2: Neural risk prediction
        with torch.no_grad():
            feature_tensor = torch.FloatTensor(features).unsqueeze(0)
            neural_predictions = self.risk_predictor(feature_tensor)
        
        # Step 3: Generate symbolic facts from features and neural outputs
        symbolic_facts = self._generate_symbolic_facts(features, neural_predictions, supplier_id)
        
        # Step 4: Symbolic reasoning
        symbolic_conclusions = self.rule_engine.evaluate_facts(symbolic_facts)
        
        # Step 5: Combine neural and symbolic results
        final_scores = self._combine_neural_symbolic(neural_predictions, symbolic_conclusions)
        
        return final_scores
    
    def _generate_symbolic_facts(self, features: np.ndarray, neural_outputs: Dict, 
                                supplier_id: str) -> Dict[str, float]:
        """Generate symbolic facts from features and neural outputs"""
        facts = {}
        
        # Extract key feature indices (you'll need to map these to your feature extraction)
        corruption_idx = 8  # Example index
        env_cert_idx = 15   # Example index
        
        # Geographic risk facts
        if len(features) > corruption_idx:
            facts['high_corruption_country'] = features[corruption_idx]
        
        # Certification facts
        if len(features) > env_cert_idx:
            facts['no_environmental_certification'] = 1.0 - features[env_cert_idx]
        
        # Neural prediction facts
        for category in ['environmental', 'social', 'governance']:
            if category in neural_outputs:
                risk_probs = neural_outputs[category][0]  # First batch item
                high_risk_prob = risk_probs[2] + risk_probs[3]  # High + Critical
                facts[f'neural_{category}_high_risk'] = high_risk_prob.item()
        
        # Recent incidents (from knowledge graph)
        esg_events = self.kg.get_esg_events(supplier_id, days_back=90)
        recent_env_incidents = sum(1 for e in esg_events if e.get('category') == 'environmental')
        facts['recent_environmental_incident'] = min(1.0, recent_env_incidents / 3.0)
        
        return facts
    
    def _combine_neural_symbolic(self, neural_outputs: Dict, 
                                symbolic_conclusions: Dict) -> Dict[str, ESGRiskScore]:
        """Combine neural and symbolic results"""
        final_scores = {}
        
        categories = ['environmental', 'social', 'governance']
        
        for i, category in enumerate(categories):
            # Get neural predictions
            neural_probs = neural_outputs[category][0]
            neural_confidence = neural_outputs['confidence'][0][i].item()
            
            # Get symbolic conclusions
            symbolic_risk_key = f'{category}_risk_high'
            symbolic_critical_key = f'{category}_risk_critical'
            
            symbolic_conf = 0.0
            symbolic_reasoning = []
            
            if symbolic_risk_key in symbolic_conclusions:
                symbolic_conf = max(symbolic_conf, symbolic_conclusions[symbolic_risk_key][0])
                symbolic_reasoning.extend(symbolic_conclusions[symbolic_risk_key][1])
            
            if symbolic_critical_key in symbolic_conclusions:
                symbolic_conf = max(symbolic_conf, symbolic_conclusions[symbolic_critical_key][0])
                symbolic_reasoning.extend(symbolic_conclusions[symbolic_critical_key][1])
            
            # Combine neural and symbolic (weighted average)
            neural_weight = 0.6
            symbolic_weight = 0.4
            
            # Convert neural probabilities to single risk score
            neural_score = sum(i * prob for i, prob in enumerate(neural_probs))
            combined_score = (neural_weight * neural_score + 
                            symbolic_weight * symbolic_conf * 3)  # Scale symbolic to 0-3
            
            # Determine risk level
            if combined_score >= 2.5:
                risk_level = RiskLevel.CRITICAL
            elif combined_score >= 2.0:
                risk_level = RiskLevel.HIGH
            elif combined_score >= 1.0:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            # Combined confidence
            combined_confidence = (neural_confidence + symbolic_conf) / 2
            
            # Add neural reasoning
            neural_reasoning = [f"Neural model prediction: {neural_score:.2f}"]
            all_reasoning = neural_reasoning + symbolic_reasoning
            
            final_scores[category] = ESGRiskScore(
                category=ESGCategory(category),
                risk_level=risk_level,
                score=combined_score,
                confidence=combined_confidence,
                reasoning=all_reasoning
            )
        
        return final_scores
    
    def analyze_supply_chain_risk(self, company_id: str) -> Dict:
        """Analyze ESG risks across entire supply chain"""
        logger.info(f"Analyzing supply chain ESG risk for company: {company_id}")
        
        # Get all suppliers in the supply chain
        with self.kg.driver.session() as session:
            query = """
            MATCH (c:Company {id: $company_id})<-[:SUPPLIES_TO*]-(s:Supplier)
            RETURN s.id as supplier_id, s.tier as tier
            ORDER BY s.tier
            """
            suppliers = session.run(query, company_id=company_id)
            supplier_list = [{"id": record["supplier_id"], "tier": record["tier"]} 
                           for record in suppliers]
        
        # Analyze each supplier
        supply_chain_risks = {}
        for supplier in supplier_list:
            supplier_id = supplier["id"]
            try:
                risk_scores = self.analyze_supplier_risk(supplier_id)
                supply_chain_risks[supplier_id] = {
                    "tier": supplier["tier"],
                    "risk_scores": risk_scores,
                    "overall_risk": max(score.score for score in risk_scores.values())
                }
            except Exception as e:
                logger.error(f"Error analyzing supplier {supplier_id}: {e}")
                continue
        
        # Calculate overall supply chain risk
        if supply_chain_risks:
            overall_risk = np.mean([s["overall_risk"] for s in supply_chain_risks.values()])
            high_risk_suppliers = [sid for sid, data in supply_chain_risks.items() 
                                 if data["overall_risk"] >= 2.0]
        else:
            overall_risk = 0.0
            high_risk_suppliers = []
        
        return {
            "company_id": company_id,
            "overall_risk_score": overall_risk,
            "high_risk_suppliers": high_risk_suppliers,
            "supplier_details": supply_chain_risks,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def generate_risk_report(self, analysis_results: Dict) -> str:
        """Generate human-readable ESG risk report"""
        report = f"""
ESG Risk Analysis Report
========================

Company: {analysis_results['company_id']}
Analysis Date: {analysis_results['analysis_timestamp']}
Overall Supply Chain Risk Score: {analysis_results['overall_risk_score']:.2f}/4.0

High Risk Suppliers ({len(analysis_results['high_risk_suppliers'])}):
{', '.join(analysis_results['high_risk_suppliers']) if analysis_results['high_risk_suppliers'] else 'None'}

Detailed Analysis:
"""
        
        for supplier_id, data in analysis_results['supplier_details'].items():
            report += f"\nSupplier: {supplier_id} (Tier {data['tier']})\n"
            report += f"Overall Risk: {data['overall_risk']:.2f}\n"
            
            for category, risk_score in data['risk_scores'].items():
                report += f"  {category.title()}: {risk_score.risk_level.name} "
                report += f"(Score: {risk_score.score:.2f}, Confidence: {risk_score.confidence:.2f})\n"
                
                if risk_score.reasoning:
                    report += f"    Reasoning:\n"
                    for reason in risk_score.reasoning[:3]:  # Limit to top 3 reasons
                        report += f"      - {reason}\n"
        
        return report
    
    def close(self):
        """Clean up resources"""
        self.kg.close()

# Example usage and testing
def create_sample_neo4j_data():
    """Create sample data structure for Neo4j (Cypher queries)"""
    return """
    // Sample Cypher queries to create test data in Neo4j
    
    // Create suppliers
    CREATE (s1:Supplier {id: 'SUP001', name: 'AcmeCorp', tier: 1, employees: 500, 
                         annual_revenue: 50000000, founded_year: 1990, sector: 'manufacturing'})
    CREATE (s2:Supplier {id: 'SUP002', name: 'GlobalTextile', tier: 2, employees: 1200, 
                         annual_revenue: 120000000, founded_year: 1985, sector: 'textiles'})
    
    // Create countries
    CREATE (c1:Country {name: 'CountryA', corruption_index: 75, environmental_performance_index: 60,
                        labor_rights_index: 80, political_stability_index: 85})
    CREATE (c2:Country {name: 'CountryB', corruption_index: 45, environmental_performance_index: 40,
                        labor_rights_index: 30, political_stability_index: 50})
    
    // Create companies
    CREATE (comp1:Company {id: 'COMP001', name: 'MegaCorp Industries'})
    
    // Create certifications
    CREATE (cert1:Certification {name: 'ISO14001', type: 'environmental', issue_date: '2023-01-15'})
    CREATE (cert2:Certification {name: 'SA8000', type: 'social', issue_date: '2022-06-10'})
    
    // Create incidents
    CREATE (inc1:Incident {id: 'INC001', category: 'environmental', severity: 7, 
                          date: '2023-11-15', description: 'Chemical spill incident'})
    CREATE (inc2:Incident {id: 'INC002', category: 'social', severity: 8, 
                          date: '2024-01-20', description: 'Labor rights violation'})
    
    // Create ESG events
    CREATE (event1:ESGEvent {id: 'ESG001', category: 'environmental', impact_score: 6,
                            date: '2024-02-10', description: 'Carbon emission increase'})
    CREATE (event2:ESGEvent {id: 'ESG002', category: 'governance', impact_score: 5,
                            date: '2024-03-05', description: 'Board diversity issue'})
    
    // Create relationships
    MATCH (s1:Supplier {id: 'SUP001'}), (c1:Country {name: 'CountryA'})
    CREATE (s1)-[:LOCATED_IN]->(c1)
    
    MATCH (s2:Supplier {id: 'SUP002'}), (c2:Country {name: 'CountryB'})
    CREATE (s2)-[:LOCATED_IN]->(c2)
    
    MATCH (s1:Supplier {id: 'SUP001'}), (cert1:Certification {name: 'ISO14001'})
    CREATE (s1)-[:HAS_CERTIFICATION]->(cert1)
    
    MATCH (s2:Supplier {id: 'SUP002'}), (inc2:Incident {id: 'INC002'})
    CREATE (s2)-[:REPORTED_INCIDENT]->(inc2)
    
    MATCH (s1:Supplier {id: 'SUP001'}), (event1:ESGEvent {id: 'ESG001'})
    CREATE (s1)-[:INVOLVED_IN]->(event1)
    
    MATCH (s1:Supplier {id: 'SUP001'}), (comp1:Company {id: 'COMP001'})
    CREATE (s1)-[:SUPPLIES_TO]->(comp1)
    
    MATCH (s2:Supplier {id: 'SUP002'}), (s1:Supplier {id: 'SUP001'})
    CREATE (s2)-[:SUPPLIES_TO]->(s1)
    """

# Example implementation and training
class ESGModelTrainer:
    """Training utilities for the neural components"""
    
    def __init__(self, esg_system: NeuroSymbolicESGSystem):
        self.esg_system = esg_system
    
    def create_synthetic_training_data(self, num_samples: int = 1000) -> Tuple[torch.Tensor, torch.Tensor]:
        """Create synthetic training data for demonstration"""
        # This would typically come from historical ESG assessments and outcomes
        
        # Generate random features (in real scenario, extract from KG)
        features = torch.randn(num_samples, 50)  # Assume 50 features
        
        # Generate synthetic labels based on feature combinations
        labels = torch.zeros(num_samples, 3, 4)  # 3 categories, 4 risk levels
        
        for i in range(num_samples):
            for cat in range(3):
                # Simple logic to create realistic labels
                risk_score = torch.sigmoid(torch.sum(features[i, cat*10:(cat+1)*10]))
                if risk_score > 0.8:
                    labels[i, cat, 3] = 1  # Critical
                elif risk_score > 0.6:
                    labels[i, cat, 2] = 1  # High
                elif risk_score > 0.4:
                    labels[i, cat, 1] = 1  # Medium
                else:
                    labels[i, cat, 0] = 1  # Low
        
        return features, labels
    
    def train_risk_predictor(self, epochs: int = 50):
        """Train the neural risk predictor"""
        if self.esg_system.risk_predictor is None:
            self.esg_system.initialize_neural_models(50)
        
        # Generate training data
        train_features, train_labels = self.create_synthetic_training_data(800)
        val_features, val_labels = self.create_synthetic_training_data(200)
        
        optimizer = optim.Adam(self.esg_system.risk_predictor.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        logger.info("Starting neural model training...")
        
        for epoch in range(epochs):
            self.esg_system.risk_predictor.train()
            
            # Forward pass
            outputs = self.esg_system.risk_predictor(train_features)
            
            # Calculate loss for each category
            total_loss = 0
            for cat_idx, category in enumerate(['environmental', 'social', 'governance']):
                pred = outputs[category]
                target = train_labels[:, cat_idx, :].argmax(dim=1)
                loss = criterion(pred, target)
                total_loss += loss
            
            # Backward pass
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
            
            # Validation
            if epoch % 10 == 0:
                self.esg_system.risk_predictor.eval()
                with torch.no_grad():
                    val_outputs = self.esg_system.risk_predictor(val_features)
                    val_loss = 0
                    for cat_idx, category in enumerate(['environmental', 'social', 'governance']):
                        pred = val_outputs[category]
                        target = val_labels[:, cat_idx, :].argmax(dim=1)
                        val_loss += criterion(pred, target)
                
                logger.info(f"Epoch {epoch}: Train Loss: {total_loss.item():.4f}, Val Loss: {val_loss.item():.4f}")
        
        logger.info("Neural model training completed!")
    
    def save_model(self, filepath: str):
        """Save trained model"""
        torch.save({
            'risk_predictor': self.esg_system.risk_predictor.state_dict(),
            'time_series_analyzer': self.esg_system.time_series_analyzer.state_dict() if self.esg_system.time_series_analyzer else None
        }, filepath)
    
    def load_model(self, filepath: str):
        """Load trained model"""
        checkpoint = torch.load(filepath)
        if self.esg_system.risk_predictor is None:
            self.esg_system.initialize_neural_models(50)
        
        self.esg_system.risk_predictor.load_state_dict(checkpoint['risk_predictor'])
        if checkpoint['time_series_analyzer'] and self.esg_system.time_series_analyzer:
            self.esg_system.time_series_analyzer.load_state_dict(checkpoint['time_series_analyzer'])

# Advanced Analytics and Visualization
class ESGAnalytics:
    """Advanced analytics for ESG risk patterns"""
    
    def __init__(self, esg_system: NeuroSymbolicESGSystem):
        self.esg_system = esg_system
    
    def risk_correlation_analysis(self, supplier_ids: List[str]) -> pd.DataFrame:
        """Analyze correlations between different ESG risk factors"""
        risk_data = []
        
        for supplier_id in supplier_ids:
            try:
                risk_scores = self.esg_system.analyze_supplier_risk(supplier_id)
                risk_data.append({
                    'supplier_id': supplier_id,
                    'environmental_score': risk_scores['environmental'].score,
                    'social_score': risk_scores['social'].score,
                    'governance_score': risk_scores['governance'].score,
                    'environmental_confidence': risk_scores['environmental'].confidence,
                    'social_confidence': risk_scores['social'].confidence,
                    'governance_confidence': risk_scores['governance'].confidence
                })
            except Exception as e:
                logger.error(f"Error analyzing supplier {supplier_id}: {e}")
                continue
        
        df = pd.DataFrame(risk_data)
        
        # Calculate correlations
        correlation_matrix = df[['environmental_score', 'social_score', 'governance_score']].corr()
        
        return df, correlation_matrix
    
    def identify_risk_patterns(self, supply_chain_analysis: Dict) -> Dict:
        """Identify patterns in supply chain risks"""
        patterns = {
            'geographic_patterns': {},
            'tier_patterns': {},
            'sector_patterns': {},
            'temporal_patterns': {}
        }
        
        # Analyze by tier
        tier_risks = {}
        for supplier_data in supply_chain_analysis['supplier_details'].values():
            tier = supplier_data['tier']
            if tier not in tier_risks:
                tier_risks[tier] = []
            tier_risks[tier].append(supplier_data['overall_risk'])
        
        for tier, risks in tier_risks.items():
            patterns['tier_patterns'][f'tier_{tier}'] = {
                'avg_risk': np.mean(risks),
                'max_risk': np.max(risks),
                'risk_variance': np.var(risks),
                'supplier_count': len(risks)
            }
        
        return patterns
    
    def risk_propagation_analysis(self, company_id: str) -> Dict:
        """Analyze how risks propagate through supply chain tiers"""
        propagation_analysis = {}
        
        # Get supply chain structure
        with self.esg_system.kg.driver.session() as session:
            query = """
            MATCH path = (c:Company {id: $company_id})<-[:SUPPLIES_TO*]-(s:Supplier)
            RETURN s.id as supplier_id, s.tier as tier, length(path) as distance
            ORDER BY tier, distance
            """
            result = session.run(query, company_id=company_id)
            supply_chain = [{'supplier_id': r['supplier_id'], 'tier': r['tier'], 
                           'distance': r['distance']} for r in result]
        
        # Calculate risk propagation by tier
        tier_risks = {}
        for supplier in supply_chain:
            supplier_id = supplier['supplier_id']
            tier = supplier['tier']
            
            try:
                risk_scores = self.esg_system.analyze_supplier_risk(supplier_id)
                avg_risk = np.mean([score.score for score in risk_scores.values()])
                
                if tier not in tier_risks:
                    tier_risks[tier] = []
                tier_risks[tier].append(avg_risk)
                
            except Exception as e:
                logger.error(f"Error in propagation analysis for {supplier_id}: {e}")
        
        # Calculate propagation metrics
        for tier in sorted(tier_risks.keys()):
            tier_avg = np.mean(tier_risks[tier])
            propagation_analysis[f'tier_{tier}'] = {
                'average_risk': tier_avg,
                'risk_variance': np.var(tier_risks[tier]),
                'high_risk_count': sum(1 for r in tier_risks[tier] if r >= 2.0),
                'supplier_count': len(tier_risks[tier])
            }
        
        return propagation_analysis

# Real-time Monitoring and Alerts
class ESGRiskMonitor:
    """Real-time ESG risk monitoring system"""
    
    def __init__(self, esg_system: NeuroSymbolicESGSystem):
        self.esg_system = esg_system
        self.alert_thresholds = {
            'critical_risk': 3.0,
            'high_risk': 2.5,
            'risk_increase': 0.5,
            'confidence_threshold': 0.7
        }
    
    def monitor_supplier_changes(self, supplier_id: str, 
                               previous_analysis: Optional[Dict] = None) -> Dict:
        """Monitor changes in supplier ESG risk"""
        current_analysis = self.esg_system.analyze_supplier_risk(supplier_id)
        
        alerts = []
        changes = {}
        
        if previous_analysis:
            for category in ['environmental', 'social', 'governance']:
                current_score = current_analysis[category].score
                previous_score = previous_analysis[category]['score']
                
                score_change = current_score - previous_score
                changes[category] = {
                    'score_change': score_change,
                    'previous_score': previous_score,
                    'current_score': current_score
                }
                
                # Generate alerts based on changes and thresholds
                if current_score >= self.alert_thresholds['critical_risk']:
                    alerts.append({
                        'type': 'CRITICAL_RISK',
                        'category': category,
                        'message': f"Critical {category} risk detected: {current_score:.2f}",
                        'severity': 'CRITICAL'
                    })
                
                elif score_change >= self.alert_thresholds['risk_increase']:
                    alerts.append({
                        'type': 'RISK_INCREASE',
                        'category': category,
                        'message': f"{category} risk increased by {score_change:.2f}",
                        'severity': 'HIGH'
                    })
        
        return {
            'supplier_id': supplier_id,
            'current_analysis': current_analysis,
            'changes': changes,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        }
    
    def batch_monitor_supply_chain(self, company_id: str) -> Dict:
        """Monitor entire supply chain for risk changes"""
        monitoring_results = []
        
        # Get all suppliers
        with self.esg_system.kg.driver.session() as session:
            query = """
            MATCH (c:Company {id: $company_id})<-[:SUPPLIES_TO*]-(s:Supplier)
            RETURN s.id as supplier_id
            """
            suppliers = [record['supplier_id'] for record in session.run(query, company_id=company_id)]
        
        # Monitor each supplier
        for supplier_id in suppliers:
            try:
                monitoring_result = self.monitor_supplier_changes(supplier_id)
                monitoring_results.append(monitoring_result)
            except Exception as e:
                logger.error(f"Error monitoring supplier {supplier_id}: {e}")
        
        # Aggregate alerts
        all_alerts = []
        for result in monitoring_results:
            all_alerts.extend(result['alerts'])
        
        # Sort alerts by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        all_alerts.sort(key=lambda x: severity_order.get(x['severity'], 4))
        
        return {
            'company_id': company_id,
            'monitoring_timestamp': datetime.now().isoformat(),
            'total_suppliers_monitored': len(monitoring_results),
            'total_alerts': len(all_alerts),
            'critical_alerts': len([a for a in all_alerts if a['severity'] == 'CRITICAL']),
            'alerts': all_alerts,
            'detailed_results': monitoring_results
        }

# Example usage and demonstration
def main_example():
    """Demonstration of the complete ESG system"""
    
    # Initialize the system (replace with your Neo4j credentials)
    esg_system = NeuroSymbolicESGSystem(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j", 
        neo4j_password="your_password"
    )
    
    try:
        # Train the neural components
        print("Training neural models...")
        trainer = ESGModelTrainer(esg_system)
        trainer.train_risk_predictor(epochs=20)
        
        # Analyze individual supplier
        print("\n" + "="*50)
        print("Individual Supplier Analysis")
        print("="*50)
        
        supplier_risk = esg_system.analyze_supplier_risk("SUP001")
        
        for category, risk_score in supplier_risk.items():
            print(f"\n{category.upper()} Risk:")
            print(f"  Level: {risk_score.risk_level.name}")
            print(f"  Score: {risk_score.score:.2f}/4.0")
            print(f"  Confidence: {risk_score.confidence:.2f}")
            print(f"  Key Reasoning:")
            for reason in risk_score.reasoning[:2]:
                print(f"    - {reason}")
        
        # Analyze entire supply chain
        print("\n" + "="*50)
        print("Supply Chain Analysis")
        print("="*50)
        
        supply_chain_analysis = esg_system.analyze_supply_chain_risk("COMP001")
        report = esg_system.generate_risk_report(supply_chain_analysis)
        print(report)
        
        # Advanced analytics
        print("\n" + "="*50)
        print("Advanced Analytics")
        print("="*50)
        
        analytics = ESGAnalytics(esg_system)
        patterns = analytics.identify_risk_patterns(supply_chain_analysis)
        
        print("Risk Patterns by Tier:")
        for tier, data in patterns['tier_patterns'].items():
            print(f"  {tier}: Avg Risk = {data['avg_risk']:.2f}, "
                  f"Suppliers = {data['supplier_count']}")
        
        # Real-time monitoring
        print("\n" + "="*50)
        print("Risk Monitoring")
        print("="*50)
        
        monitor = ESGRiskMonitor(esg_system)
        monitoring_results = monitor.batch_monitor_supply_chain("COMP001")
        
        print(f"Monitored {monitoring_results['total_suppliers_monitored']} suppliers")
        print(f"Generated {monitoring_results['total_alerts']} alerts")
        print(f"Critical alerts: {monitoring_results['critical_alerts']}")
        
        if monitoring_results['alerts']:
            print("\nTop Alerts:")
            for alert in monitoring_results['alerts'][:3]:
                print(f"  [{alert['severity']}] {alert['message']}")
        
    except Exception as e:
        logger.error(f"Error in main example: {e}")
    
    finally:
        esg_system.close()

if __name__ == "__main__":
    print("Neuro-Symbolic ESG Risk Analysis System for Supply Chains")
    print("="*60)
    print()
    print("This system combines:")
    print("- Neural networks for pattern recognition and risk prediction")
    print("- Neo4j knowledge graph for supply chain relationships")
    print("- Symbolic reasoning for ESG rule evaluation")
    print("- Real-time monitoring and alerting")
    print()
    
    # Uncomment to run the full example (requires Neo4j setup)
    # main_example()
    
    print("Sample Neo4j setup queries:")
    print(create_sample_neo4j_data())