# Diagram Options for Oct 22 Presentation

**Last Updated**: October 18, 2025 20:30 UTC
**Purpose**: Oct 22 presentation - choose best diagrams for your slides

---

## ⭐ NEW: High-Resolution Paper Figure (600 DPI)

**File**: `figure3_detection_vs_profitability_600dpi.png` (478 KB)

**Features**:
- ✅ **600 DPI** - Presentation/poster quality (vs 300 DPI paper version)
- ✅ **THE critical figure** - Detection stable while profitability declines
- ✅ **Optimized layout** - No visual collisions, full y-axis utilization
- ✅ **Q1-Q4 2024 data** - Complete year validation results
- ✅ **Polished Oct 18** - Final visual refinement complete

**Use When**:
- Oct 22 presentation slides (high-quality display)
- Poster printing
- Need to emphasize detection-profitability divergence
- **This is THE visual anchor of the research**

**Location**: Same folder as other diagrams

---

## Available Diagrams (9 versions total, 5 diagram types)

### 🎯 RECOMMENDED FOR PRESENTATION

#### Option 1: **Compact Flow** (BEST FOR SINGLE SLIDE)
**File**: `system_flow_compact.png`

**Features**:
- ✅ **5 key components** (easy to explain in 2-3 minutes)
- ✅ **Vertical flow** (fits slide well)
- ✅ **Emoji icons** (visually engaging)
- ✅ **Shows complete pipeline**: Data → Processing → AI → Validation → Results
- ✅ **Includes Alpha Vantage API + Cache**
- ✅ **Key metrics shown**: 71.5% detection, 91.2% accuracy

**Use When**:
- Single slide in presentation
- Need to explain system quickly
- Audience is non-technical or mixed

**Size**: ~10" wide × 12" tall (fits PowerPoint slide perfectly)

---

#### Option 2: **Layered Architecture** (DETAILED, VERTICAL)
**File**: `system_architecture_layered.png`

**Features**:
- ✅ **Shows ALL components** (13 nodes)
- ✅ **Grouped by function** (Data Sources, Processing, LLM, Validation)
- ✅ **Cache system visible**: "Check cache → API if needed"
- ✅ **Alpha Vantage API** explicitly shown
- ✅ **Both LLM models**: GPT-4o-mini (tool) + o3-mini (reasoning)
- ✅ **Vertical layout** (not linear bar)

**Use When**:
- Technical audience
- Need to show complete system
- Have 2-3 slides for architecture

**Size**: ~12" wide × 14" tall

---

#### Option 3: **Swim Lanes** (HORIZONTAL, BY LAYER)
**File**: `system_architecture_swimlanes.png`

**Features**:
- ✅ **4 swim lanes**: Data → Processing → AI → Validation
- ✅ **Shows system organization** clearly
- ✅ **Cache DB shown as cylinder** (database icon)
- ✅ **Alpha Vantage API** visible in Data Layer
- ✅ **Horizontal flow** (left to right)
- ✅ **Professional look** (good for technical presentation)

**Use When**:
- Technical/academic audience
- Want to emphasize system architecture layers
- Discussing component responsibilities

**Size**: ~16" wide × 10" tall (landscape slide)

---

### 📋 OTHER OPTIONS

#### Option 4: **Original Detailed** (LINEAR BAR - NOT RECOMMENDED FOR SLIDES)
**File**: `system_architecture.pdf` / `system_architecture_slides.png`

**Features**:
- 6 nodes in linear left-to-right flow
- PDF vector format
- Good for paper, not ideal for slides

**Why Not**: Linear bar format doesn't fit slide well (you mentioned this issue)

---

#### Option 5: **Simplified** (4 STAGES, HORIZONTAL)
**File**: `system_architecture_simple.png`

**Features**:
- 4 components only
- Very simple
- Horizontal bar (same issue as Option 4)

**Why Not**: Still linear bar format

---

## Quick Comparison

| Diagram | Layout | Components | Alpha Vantage? | Cache? | Best For |
|---------|--------|------------|----------------|--------|----------|
| **Compact Flow** ⭐ | Vertical | 5 | ✅ | ✅ | **Single slide** |
| **Layered** ⭐⭐ | Vertical | 13 | ✅ | ✅ | **Detailed presentation** |
| **Swim Lanes** ⭐⭐ | Horizontal | 11 | ✅ | ✅ | **Technical audience** |
| Original Detailed | Horizontal bar | 6 | ❌ | ❌ | Paper only |
| Simplified | Horizontal bar | 4 | ❌ | ❌ | Not recommended |

---

## Recommended Selection by Audience

### General Research Presentation
**Use**: `system_flow_compact.png`
- Quick to explain (2-3 minutes)
- Shows complete pipeline
- Visually clean
- Fits single slide perfectly

### Technical/Academic Conference
**Use**: `system_architecture_layered.png`
- Shows all technical details
- Grouped by function
- Cache system visible
- Can discuss each layer

### PhD Defense / Detailed Review
**Use**: Both
1. Start with `system_flow_compact.png` (overview)
2. Follow with `system_architecture_layered.png` (details)

---

## Key Features Across All Diagrams

### ✅ Accurately Shows:
- **Alpha Vantage API** as data source
- **Cache system** (SQLite DB with "check cache first" logic)
- **Correct LLM models**:
  - GPT-4o-mini for tool calling
  - o3-mini for reasoning
- **Complete flow**: Data → GEX → Obfuscation → LLM → Validation
- **Key results**: 71.5% detection, 91.2% accuracy

### ❌ No Longer Shows:
- "GPT-4" (incorrect - fixed in all new versions)
- Missing cache system (now included)
- Missing data source details (now included)

---

## File Sizes

| File | Size | Format | DPI |
|------|------|--------|-----|
| system_flow_compact.png | ~80 KB | PNG | 300 |
| system_architecture_layered.png | ~120 KB | PNG | 300 |
| system_architecture_swimlanes.png | ~100 KB | PNG | 300 |
| system_architecture.pdf | ~12 KB | Vector PDF | N/A |

All PNG files are 300 DPI - suitable for high-quality slides and printing.

---

## Usage in PowerPoint/Beamer

### PowerPoint
1. Insert → Picture → Browse
2. Select `system_flow_compact.png` (or your choice)
3. Resize to fit slide (maintain aspect ratio)
4. Recommended: Full width, centered

### Beamer (LaTeX)
```latex
\begin{frame}{System Architecture}
  \centering
  \includegraphics[width=0.9\textwidth]{diagrams/system_flow_compact.png}

  \vspace{1em}
  Complete validation pipeline from data source to results
\end{frame}
```

---

## My Recommendation

**For Oct 22 Presentation**: Use **`system_flow_compact.png`**

**Rationale**:
1. ✅ Fits single slide perfectly (vertical layout)
2. ✅ Shows complete system (Alpha Vantage + Cache + all stages)
3. ✅ Quick to explain (5 components, clear flow)
4. ✅ Visually engaging (emoji icons, colors)
5. ✅ Includes key metrics (71.5%, 91.2%)
6. ✅ **Not a horizontal bar** (solves your concern!)

**Backup**: If audience is very technical, switch to `system_architecture_layered.png` for more detail.

---

## Additional Diagrams (Complete Set)

### Diagram 2: **Pattern Taxonomy** ⭐⭐
**File**: `pattern_taxonomy.png` (292 KB)

**Features**:
- ✅ **3-level hierarchy**: Pattern Types → Categories → Specific Patterns
- ✅ **Color-coded**: Green (structural/validated), Yellow (statistical), Red (narrative/failed)
- ✅ **Shows validation results**: 100% detection, 86-96% accuracy
- ✅ **Clear distinction**: Mechanical vs context-dependent patterns

**Use When**:
- Explaining pattern classification methodology
- Showing which patterns passed validation
- Discussing obfuscation testing criteria

---

### Diagram 3: **WHO→WHOM→WHAT Framework** ⭐⭐
**File**: `causal_framework.png` (239 KB)

**Features**:
- ✅ **Causal chain visualization**: WHO → WHOM → WHAT
- ✅ **Concrete example**: Gamma Positioning pattern breakdown
- ✅ **Clear definitions**: Market participants, constraints, forced actions
- ✅ **Left-to-right flow**: Easy to follow causality

**Use When**:
- Explaining causal identification methodology
- Technical audience interested in detection logic
- Discussing why some patterns are mechanical

---

### Diagram 4: **Data Flow Pipeline** ⭐
**File**: `data_flow_pipeline.png` (404 KB)

**Features**:
- ✅ **Complete 6-stage flow**: Raw Data → GEX → Obfuscation → LLM → Outcomes → Validation
- ✅ **Shows transformations**: Each processing step clearly labeled
- ✅ **Detailed example**: Actual data from Jan 2, 2024
- ✅ **Vertical layout**: Top to bottom, fits slide
- ⚠️ **Very detailed**: May be too much for single slide

**Use When**:
- Detailed technical presentation
- PhD defense or committee review
- Need to explain complete pipeline with examples

**Warning**: High information density - consider using Compact Flow (Option 1) for general audience

---

### Diagram 5: **Methodology Overview** ⭐⭐⭐
**File**: `methodology_overview.png` (440 KB)

**Features**:
- ✅ **Before/After obfuscation**: Clear visual comparison
- ✅ **Shows WHAT is removed**: Dates, tickers, events
- ✅ **Shows WHAT is preserved**: GEX values, spot prices
- ✅ **Validation results**: All 3 patterns passed (100% detection)
- ✅ **Novel contribution**: Highlights obfuscation testing innovation

**Use When**:
- Explaining the novel validation methodology
- Distinguishing from prior work
- Emphasizing academic contribution
- Research presentation (highly recommended!)

---

## Complete Diagram Inventory

| # | Diagram Type | File | Size | Best For |
|---|--------------|------|------|----------|
| 1 | System Architecture (Compact) | system_flow_compact.png | 164 KB | ⭐⭐⭐ General audience |
| 2 | System Architecture (Layered) | system_architecture_layered.png | 371 KB | ⭐⭐ Technical audience |
| 3 | System Architecture (Swim Lanes) | system_architecture_swimlanes.png | 214 KB | ⭐⭐ Technical audience |
| 4 | Pattern Taxonomy | pattern_taxonomy.png | 292 KB | ⭐⭐ Classification explanation |
| 5 | WHO→WHOM→WHAT Framework | causal_framework.png | 239 KB | ⭐⭐ Methodology detail |
| 6 | Data Flow Pipeline | data_flow_pipeline.png | 404 KB | ⭐ Very detailed/technical |
| 7 | Methodology Overview | methodology_overview.png | 440 KB | ⭐⭐⭐ Novel contribution |

---

## Recommended Presentation Flow (Oct 22)

### Option A: Concise Presentation (3 slides)
1. **Slide 1**: `system_flow_compact.png` - System overview
2. **Slide 2**: `methodology_overview.png` - Novel validation approach
3. **Slide 3**: `pattern_taxonomy.png` - Results (3 patterns validated)

**Rationale**: Covers complete story in 3 diagrams - What we built, How we validated, What we found

### Option B: Detailed Presentation (5 slides)
1. **Slide 1**: `system_flow_compact.png` - System overview
2. **Slide 2**: `causal_framework.png` - WHO→WHOM→WHAT framework
3. **Slide 3**: `methodology_overview.png` - Obfuscation testing
4. **Slide 4**: `pattern_taxonomy.png` - Pattern classification
5. **Slide 5**: Results table (not a diagram - use YAML data)

**Rationale**: More methodological detail, good for technical audience

### Option C: PhD Defense (6+ slides)
1. **Slide 1**: `system_flow_compact.png` - Overview
2. **Slide 2**: `system_architecture_layered.png` - Complete architecture
3. **Slide 3**: `causal_framework.png` - Causal identification
4. **Slide 4**: `methodology_overview.png` - Obfuscation testing
5. **Slide 5**: `pattern_taxonomy.png` - Classification and results
6. **Slide 6**: `data_flow_pipeline.png` - Example walkthrough

**Rationale**: Maximum detail for committee review

---

## Next Steps

1. ✅ All 5 diagram types generated (9 versions total)
2. ⏳ Choose presentation flow (Option A, B, or C)
3. ⏳ Insert diagrams into slide deck
4. ⏳ Test visibility from back of room (font sizes, colors)
5. ⏳ Prepare speaker notes for each diagram

---

**All diagrams available in**: `docs/presentations/oct22_research/diagrams/`

**Generation Scripts**:
- `generate_system_architecture.py` - Original 6-stage pipeline
- `generate_system_architecture_v2.py` - Slide-friendly versions
- `generate_pattern_taxonomy.py` - 3-level hierarchy
- `generate_causal_framework.py` - WHO→WHOM→WHAT
- `generate_data_flow.py` - Detailed pipeline with examples
- `generate_methodology_overview.py` - Obfuscation testing
