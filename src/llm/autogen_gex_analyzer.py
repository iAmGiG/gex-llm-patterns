"""
LLM Integration with Autogen Framework for GEX Pattern Analysis
Integrates Microsoft Autogen-agent chat framework for sophisticated LLM-based pattern analysis.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.tokenization.sequence_builder import SequenceBuilder


class ModelType(Enum):
    """Available OpenAI models for routing."""
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"


@dataclass
class PatternAnalysisResult:
    """Structured result from LLM pattern analysis."""
    pattern_id
    mechanical_explanation
    failure_modes
    trading_implications
    confidence_score
    statistical_significance
    cost_analysis


class CostOptimizer:
    """Cost optimization for routing requests between GPT-4o-mini and GPT-4o."""
    
    def __init__(self):
        # Current OpenAI pricing (per 1K tokens)
        self.pricing = {
            ModelType.GPT_4O_MINI: {"input": 0.00015, "output": 0.0006},
            ModelType.GPT_4O: {"input": 0.03, "output": 0.06}
        }
        
    def estimate_cost(self, model: ModelType, input_tokens, output_tokens = 500) -> float:
        """Estimate cost for a request."""
        pricing = self.pricing[model]
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000
        
    def route_request(self, pattern_data) -> ModelType:
        """Route request to appropriate model based on complexity and significance."""
        # Get pattern characteristics
        complexity_score = pattern_data.get('complexity_score', 0.5)
        statistical_significance = pattern_data.get('p_value', 1.0)
        support_count = pattern_data.get('support', 0)
        
        # High-value patterns get GPT-4o treatment
        if (statistical_significance < 0.01 and support_count > 50) or complexity_score > 0.8:
            return ModelType.GPT_4O
        
        # Everything else uses cost-effective GPT-4o-mini
        return ModelType.GPT_4O_MINI


class GEXPromptTemplates:
    """Sophisticated prompt templates for GEX pattern analysis."""
    
    SYSTEM_PROMPT = """You are an expert in market microstructure and dealer hedging mechanics. 
You understand how gamma exposure affects market maker behavior and creates predictable price movements.

Key concepts:
- Dealers hedge gamma dynamically, buying rallies and selling dips when GEX > 0
- Negative GEX creates unstable conditions where dealers amplify moves  
- Gamma flip points create regime changes in market behavior
- Options expiration affects dealer positioning and market volatility
- Transaction costs and bid-ask spreads affect pattern reliability

Focus on mechanical explanations of dealer behavior, not generic market commentary.
"""

    PATTERN_ANALYSIS_TEMPLATE = """Given this market pattern discovered in historical data:

Pattern Sequence: {pattern_sequence}
Historical Accuracy: {accuracy}% ({support} occurrences)
Statistical Significance: p = {p_value}
Lift vs Random: {lift}x
Sharpe Ratio: {sharpe}

Market Context:
- Average GEX level: {avg_gex}
- Typical volatility: {avg_vix}
- Market regime: {regime}
- Days to expiration: {dte_avg}

Explain the mechanical reason this pattern occurs, focusing specifically on:
1. How dealer gamma hedging creates this pattern
2. Why it leads to the observed price movement  
3. Under what market conditions it's most/least reliable
4. Potential risks or failure modes
5. Transaction cost considerations

Provide a confidence score (0-1) for your explanation."""

    SKEPTIC_REVIEW_TEMPLATE = """Review this pattern analysis for potential flaws:

Original Analysis: {analysis}
Pattern Statistics: {statistics}

Consider these potential issues:
1. Survivorship bias - are we only seeing successful patterns?
2. Multiple testing - how many patterns were tested vs significant results?
3. Market regime dependence - does this only work in specific conditions?
4. Transaction costs - are returns realistic after costs?
5. Sample size adequacy - is the support statistically meaningful?
6. Look-ahead bias - does the pattern use future information?

Provide specific concerns and rate the analysis reliability (0-1)."""

    VALIDATOR_SYNTHESIS_TEMPLATE = """Synthesize the pattern analysis and critique into a final assessment:

Pattern Analysis: {analysis}
Skeptical Review: {critique}
Pattern Statistics: {statistics}

Provide:
1. Final mechanical explanation (incorporating valid criticisms)
2. Confidence score (0-1) accounting for statistical and methodological concerns
3. Trading implications with specific entry/exit criteria
4. Risk management recommendations
5. Position sizing guidance based on pattern reliability

Format as structured JSON for parsing."""


class AutogenGEXAnalyzer:
    """Main class for LLM-based GEX pattern analysis using Autogen framework."""
    
    def __init__(self, config_path= None):
        """Initialize the analyzer with configuration."""
        self.config = self._load_config(config_path)
        self.cost_optimizer = CostOptimizer()
        self.prompt_templates = GEXPromptTemplates()
        
        # Initialize OpenAI clients
        self._init_openai_clients()
        
        # Initialize agents
        self._init_agents()
        
    def _load_config(self, config_path= None) :
        """Load configuration from config.json."""
        if config_path is None:
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "config.json"
            
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        return {
            'openai_api_key': config['OPEN_AI_KEY'],
            'model': config['OPEN_MODEL']
        }
        
    def _init_openai_clients(self):
        """Initialize OpenAI clients for both models."""
        self.clients = {
            ModelType.GPT_4O_MINI: OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                api_key=self.config['openai_api_key']
            ),
            ModelType.GPT_4O: OpenAIChatCompletionClient(
                model="gpt-4o", 
                api_key=self.config['openai_api_key']
            )
        }
        
    def _init_agents(self):
        """Initialize the multi-agent team."""
        # Market Microstructure Analyst
        self.analyst_agent = AssistantAgent(
            "analyst",
            model_client=self.clients[ModelType.GPT_4O_MINI],
            system_message=self.prompt_templates.SYSTEM_PROMPT + 
                          "\n\nYou are the Market Microstructure Analyst. Provide detailed mechanical explanations of dealer hedging patterns."
        )
        
        # Statistical Skeptic  
        self.skeptic_agent = AssistantAgent(
            "skeptic",
            model_client=self.clients[ModelType.GPT_4O_MINI],
            system_message=self.prompt_templates.SYSTEM_PROMPT +
                          "\n\nYou are the Statistical Skeptic. Challenge analyses for methodological flaws and statistical validity."
        )
        
        # Pattern Validator
        self.validator_agent = AssistantAgent(
            "validator",
            model_client=self.clients[ModelType.GPT_4O_MINI],
            system_message=self.prompt_templates.SYSTEM_PROMPT +
                          "\n\nYou are the Pattern Validator. Synthesize analyses into actionable trading insights with confidence scores."
        )
        
    async def analyze_pattern(self, pattern_data) -> PatternAnalysisResult:
        """Analyze a pattern using multi-agent conversation flow."""
        
        # Route to appropriate model based on pattern significance
        model_type = self.cost_optimizer.route_request(pattern_data)
        
        # Update agents with appropriate model if high-value pattern
        if model_type == ModelType.GPT_4O:
            await self._upgrade_agents_to_gpt4()
        
        # Stage 1: Initial analysis by Market Microstructure Analyst
        analysis_prompt = self.prompt_templates.PATTERN_ANALYSIS_TEMPLATE.format(**pattern_data)
        
        # Create group chat for multi-agent conversation
        group_chat = RoundRobinGroupChat([
            self.analyst_agent,
            self.skeptic_agent, 
            self.validator_agent
        ])
        
        # Run the conversation
        chat_result = await group_chat.run(
            task=TextMessage(content=analysis_prompt, source="user")
        )
        
        # Parse results from the conversation
        result = self._parse_conversation_result(chat_result, pattern_data, model_type)
        
        return result
        
    async def _upgrade_agents_to_gpt4(self):
        """Upgrade agents to GPT-4o for high-value patterns."""
        self.analyst_agent.model_client = self.clients[ModelType.GPT_4O]
        self.skeptic_agent.model_client = self.clients[ModelType.GPT_4O]  
        self.validator_agent.model_client = self.clients[ModelType.GPT_4O]
        
    def _parse_conversation_result(self, chat_result, pattern_data, model_type: ModelType) -> PatternAnalysisResult:
        """Parse the multi-agent conversation into structured results."""
        
        # Extract messages from conversation
        messages = chat_result.messages if hasattr(chat_result, 'messages') else []
        
        # Find the final synthesis from validator agent
        validator_response = None
        for msg in reversed(messages):
            if hasattr(msg, 'source') and msg.source == "validator":
                validator_response = msg.content
                break
                
        if not validator_response:
            # Fallback if no validator response found
            validator_response = str(messages[-1].content) if messages else "{}"
        
        # Try to parse JSON response, fall back to text parsing
        try:
            parsed_result = json.loads(validator_response)
        except json.JSONDecodeError:
            parsed_result = self._fallback_text_parsing(validator_response)
            
        # Calculate cost analysis
        estimated_input_tokens = len(str(pattern_data)) // 4  # Rough estimate
        estimated_output_tokens = len(validator_response) // 4
        cost_analysis = {
            'model_used': model_type.value,
            'estimated_cost': self.cost_optimizer.estimate_cost(model_type, estimated_input_tokens, estimated_output_tokens),
            'input_tokens_est': estimated_input_tokens,
            'output_tokens_est': estimated_output_tokens
        }
        
        return PatternAnalysisResult(
            pattern_id=pattern_data.get('pattern_id', 'unknown'),
            mechanical_explanation=parsed_result.get('mechanical_explanation', {}),
            failure_modes=parsed_result.get('failure_modes', []),
            trading_implications=parsed_result.get('trading_implications', {}),
            confidence_score=parsed_result.get('confidence_score', 0.5),
            statistical_significance=pattern_data.get('p_value', 1.0),
            cost_analysis=cost_analysis
        )
        
    def _fallback_text_parsing(self, text) :
        """Fallback text parsing if JSON parsing fails."""
        return {
            'mechanical_explanation': {'summary': text[:500]},
            'failure_modes': ['Unable to parse structured response'],
            'trading_implications': {'note': 'Manual review required'},
            'confidence_score': 0.3
        }
        
    def get_cost_summary(self) :
        """Get summary of cost optimization settings."""
        return {
            'pricing': self.cost_optimizer.pricing,
            'routing_logic': 'High significance patterns (p < 0.01, support > 50) → GPT-4o, others → GPT-4o-mini',
            'estimated_cost_difference': '200x cheaper for GPT-4o-mini vs GPT-4o'
        }


class TokenizedPatternProcessor:
    """Process tokenized sequences into pattern data for LLM analysis."""
    
    def __init__(self, sequence_builder: SequenceBuilder):
        self.sequence_builder = sequence_builder
        
    def prepare_pattern_for_llm(self, tokenized_sequence, 
                               statistics) :
        """Convert tokenized pattern into structured data for LLM analysis."""
        
        # Extract pattern characteristics
        pattern_sequence = " → ".join(tokenized_sequence)
        
        # Calculate complexity score based on unique tokens and length
        unique_tokens = len(set(tokenized_sequence))
        complexity_score = min(1.0, (unique_tokens * len(tokenized_sequence)) / 100)
        
        # Determine market regime from tokens
        regime = self._determine_market_regime(tokenized_sequence)
        
        return {
            'pattern_id': f"P{hash(pattern_sequence) % 10000:04d}",
            'pattern_sequence': pattern_sequence,
            'accuracy': statistics.get('success_rate', 0) * 100,
            'support': statistics.get('occurrence_count', 0),
            'p_value': statistics.get('p_value', 1.0),
            'lift': statistics.get('lift_ratio', 1.0),
            'sharpe': statistics.get('sharpe_ratio', 0.0),
            'avg_gex': statistics.get('avg_gex_level', 0.0),
            'avg_vix': statistics.get('avg_volatility', 20.0),
            'regime': regime,
            'dte_avg': statistics.get('avg_days_to_expiry', 30),
            'complexity_score': complexity_score
        }
        
    def _determine_market_regime(self, tokens) -> str:
        """Determine market regime from token sequence."""
        
        # Count different token types
        gex_neg_count = sum(1 for token in tokens if 'NEG' in token)
        gex_pos_count = sum(1 for token in tokens if 'POS' in token) 
        vol_spike_count = sum(1 for token in tokens if 'VOL_SPIKE' in token)
        
        if gex_neg_count > gex_pos_count:
            return "Negative GEX Regime"
        elif vol_spike_count > 0:
            return "High Volatility Regime"
        else:
            return "Positive GEX Regime"