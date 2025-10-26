# Agent Framework Documentation

## Microsoft Autogen Integration

This project leverages Microsoft's Autogen framework for multi-agent LLM conversations, enabling sophisticated pattern analysis through coordinated AI agents.

## Agent Architecture

### Multi-Agent Pattern Analysis Team

```python
class PatternAnalysisTeam:
    def __init__(self):
        self.analyst = Agent("Market Microstructure Analyst")
        self.skeptic = Agent("Statistical Skeptic") 
        self.validator = Agent("Pattern Validator")
        self.coordinator = Agent("Research Coordinator")
```

### Agent Roles

#### 1. Market Microstructure Analyst

- **Purpose**: Explain discovered patterns through market mechanics
- **Expertise**: Dealer hedging, gamma exposure, market microstructure
- **Responsibilities**:
  - Interpret GEX patterns mechanistically
  - Explain dealer behavior implications
  - Connect patterns to known market phenomena

#### 2. Statistical Skeptic  

- **Purpose**: Challenge pattern validity and statistical significance
- **Expertise**: Statistical testing, data mining bias, false discoveries
- **Responsibilities**:
  - Question pattern robustness
  - Identify potential statistical issues
  - Suggest additional validation tests

#### 3. Pattern Validator

- **Purpose**: Synthesize analysis and provide final assessment
- **Expertise**: Research methodology, pattern validation, synthesis
- **Responsibilities**:
  - Integrate analyst and skeptic perspectives
  - Provide balanced final assessment
  - Recommend trading implications and limitations

#### 4. Research Coordinator

- **Purpose**: Manage workflow and ensure research quality
- **Expertise**: Research methodology, project management
- **Responsibilities**:
  - Route patterns to appropriate agents
  - Ensure consistent quality standards
  - Coordinate multi-pattern analysis

## Agent Conversation Flows

### Pattern Analysis Workflow

```python
┌─────────────────┐
│  New Pattern    │
│   Discovered    │
└─────────┬───────┘
          │
┌─────────▼───────┐
│   Coordinator   │ ── Route to Analysis Team
│  Prioritizes    │
└─────────┬───────┘
          │
┌─────────▼───────┐    ┌─────────────────┐    ┌─────────────────┐
│    Analyst      │    │    Skeptic      │    │   Validator     │
│   Explains      │────│   Challenges    │────│  Synthesizes   │
│  Mechanics      │    │   Validity      │    │  Final Result  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Sample Conversation

```python
# Stage 1: Initial Analysis
analyst_prompt = f"""
Pattern: {pattern.sequence}
Accuracy: {pattern.confidence}% ({pattern.support} occurrences)

Explain why this pattern works mechanistically, focusing on:
1. Dealer gamma hedging behavior
2. Market microstructure implications
3. Regime-dependent factors
"""

# Stage 2: Critical Review
skeptic_prompt = f"""
The analyst claims: {analyst_response}

Statistical context:
- p-value: {pattern.p_value}
- Lift ratio: {pattern.lift}
- Sample size: {pattern.support}

What are the statistical concerns and potential failure modes?
"""

# Stage 3: Synthesis
validator_prompt = f"""
Analyst perspective: {analyst_response}
Skeptic concerns: {skeptic_response}

Provide a balanced assessment:
1. Pattern reliability score (1-10)
2. Key limitations and risks
3. Trading implementation recommendations
"""
```

## Prompt Engineering Framework

### System Prompts

#### Market Microstructure Analyst

```python
ANALYST_SYSTEM_PROMPT = """
You are an expert in market microstructure and dealer hedging mechanics.

Key Knowledge:
- Dealers hedge gamma dynamically (buy rallies/sell dips when GEX > 0)
- Negative GEX creates unstable conditions where dealers amplify moves  
- Gamma flip points create regime changes in market behavior
- Options expiration affects dealer positioning and volatility

Your responses should focus on mechanical explanations, not generic commentary.
"""
```

#### Statistical Skeptic

```python
SKEPTIC_SYSTEM_PROMPT = """
You are a statistical expert focused on identifying flaws in financial pattern analysis.

Your role is to:
- Question statistical significance and robustness
- Identify potential data mining bias
- Point out regime dependency and overfitting risks
- Suggest additional validation tests

Be constructively critical and specific about statistical concerns.
"""
```

#### Pattern Validator  

```python
VALIDATOR_SYSTEM_PROMPT = """
You synthesize market analysis with statistical critique to provide balanced assessments.

Your role is to:
- Weigh analyst explanations against skeptic concerns
- Provide practical implementation guidance
- Assign realistic confidence scores
- Identify key risks and limitations

Focus on actionable research conclusions.
"""
```

### Dynamic Context Injection

```python
def build_context(pattern, market_data):
    return {
        'pattern_context': {
            'sequence': pattern.sequence,
            'statistical_metrics': pattern.stats,
            'occurrence_dates': pattern.dates
        },
        'market_context': {
            'avg_gex_level': calculate_avg_gex(pattern.dates),
            'volatility_regime': classify_volatility(pattern.dates), 
            'market_events': identify_events(pattern.dates)
        },
        'historical_context': {
            'similar_patterns': find_similar(pattern),
            'regime_performance': test_across_regimes(pattern)
        }
    }
```

## Cost Optimization Strategy

### Model Selection Logic

```python
class ModelRouter:
    def __init__(self):
        self.costs = {
            'gpt-4o-mini': 0.000150,  # per 1K tokens
            'gpt-4o': 0.030000        # per 1K tokens (200x more expensive)
        }
        
    def route_pattern(self, pattern):
        # Use cheaper model for most patterns
        if pattern.significance_score < 0.7:
            return 'gpt-4o-mini'
        
        # Use expensive model only for high-value patterns    
        elif pattern.p_value < 0.001 and pattern.lift > 2.0:
            return 'gpt-4o'
            
        else:
            return 'skip'  # Not worth analysis cost
```

### Batch Processing

- Group similar patterns for efficient analysis
- Reuse context across related patterns
- Minimize redundant agent conversations

## Agent Configuration

### Environment Setup

```python
# Check conda environment for Autogen dependencies
from autogen_core.tools import FunctionTool
from autogen_core.agents import AssistantAgent, UserProxyAgent

# Reference implementation in docs/legacy/autogen_examples.py (legacy)
# Current implementation: src/llm/autogen_market_mechanics.py
```

### Agent Initialization

```python
def create_analysis_team():
    analyst = AssistantAgent(
        name="microstructure_analyst",
        system_message=ANALYST_SYSTEM_PROMPT,
        llm_config={"model": "gpt-4o-mini"}
    )
    
    skeptic = AssistantAgent(
        name="statistical_skeptic", 
        system_message=SKEPTIC_SYSTEM_PROMPT,
        llm_config={"model": "gpt-4o-mini"}
    )
    
    validator = AssistantAgent(
        name="pattern_validator",
        system_message=VALIDATOR_SYSTEM_PROMPT, 
        llm_config={"model": "gpt-4o"}  # Use better model for synthesis
    )
    
    return analyst, skeptic, validator
```

## Quality Assurance

### Response Validation

- Check for mechanical explanations (not generic market commentary)
- Validate statistical reasoning quality
- Ensure actionable conclusions

### Conversation Monitoring

- Track token usage and costs
- Monitor response quality metrics  
- Log conversation flows for analysis

### Error Handling

- Graceful degradation when models unavailable
- Retry logic for transient failures
- Fallback to single-agent analysis if needed

## Integration Points

### Input: Pattern Mining Results

- Statistical significance metrics
- Historical occurrence data
- Market context information

### Output: Validated Insights

- Mechanical explanations
- Statistical assessments  
- Trading implementation guidance
- Risk and limitation documentation

### Integration with Validation Pipeline

- Feed insights to backtesting framework
- Support statistical validation testing
- Provide input for research documentation
