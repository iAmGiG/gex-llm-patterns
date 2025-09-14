"""
Level Aggregator - GEX Aggregation and Analysis

Aggregates gamma exposure data across different dimensions:
- Strike-level aggregation
- Expiration-level aggregation  
- Support/resistance level identification
- Multi-timeframe GEX analysis
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class LevelAggregator:
    """
    Aggregate and analyze GEX data across multiple dimensions for
    comprehensive market structure analysis.
    """
    
    def __init__(self, 
                 significant_gex_threshold = 5000000,
                 clustering_threshold = 0.02):
        """
        Initialize Level Aggregator.
        
        Args:
            significant_gex_threshold: Minimum absolute GEX to consider significant
            clustering_threshold: Price clustering threshold (as % of underlying)
        """
        self.significant_gex_threshold = significant_gex_threshold
        self.clustering_threshold = clustering_threshold
        
    def aggregate_by_expiration(self, 
                              options_data,
                              gex_data) :
        """
        Aggregate GEX by expiration date.
        
        Args:
            options_data: Original options data with expiration info
            gex_data: GEX calculation results
            
        Returns:
            DataFrame with GEX aggregated by expiration
        """
        if options_data.empty or gex_data.empty:
            return pd.DataFrame()
            
        # Check what expiration columns are available
        exp_date_col = None
        if 'expiration_date' in gex_data.columns:
            exp_date_col = 'expiration_date'
        elif 'expiration' in gex_data.columns:
            exp_date_col = 'expiration'
        elif 'expiration_date' in options_data.columns:
            exp_date_col = 'expiration_date'
        elif 'expiration' in options_data.columns:
            exp_date_col = 'expiration'
        
        if exp_date_col is None:
            logger.warning("No expiration date column found for aggregation")
            return pd.DataFrame()
        
        # Use gex_data if it already has the expiration info, otherwise merge
        if exp_date_col in gex_data.columns and 'days_to_expiration' in gex_data.columns:
            merged_data = gex_data.copy()
        else:
            # Simple merge approach - just add the needed columns
            merged_data = gex_data.copy()
            
            # Add expiration information from original data
            if exp_date_col in options_data.columns:
                merged_data[exp_date_col] = options_data[exp_date_col]
            
            # Ensure days_to_expiration exists
            if 'days_to_expiration' not in merged_data.columns:
                if exp_date_col in merged_data.columns:
                    if 'date' in merged_data.columns:
                        merged_data['days_to_expiration'] = (merged_data[exp_date_col] - merged_data['date']).dt.days
                    else:
                        current_date = pd.Timestamp.now().normalize()
                        merged_data['days_to_expiration'] = (merged_data[exp_date_col] - current_date).dt.days
            
        # Aggregate by expiration
        exp_aggregation = merged_data.groupby([exp_date_col, 'days_to_expiration']).agg({
            'weighted_gex': ['sum', 'count'],
            'open_interest': 'sum',
            'bs_gamma': 'sum'
        }).reset_index()
        
        # Flatten column names
        exp_aggregation.columns = [
            'expiration_date', 'days_to_expiration', 
            'total_gex', 'contract_count', 'total_oi', 'total_gamma'
        ]
        
        # Sort by expiration
        exp_aggregation = exp_aggregation.sort_values('days_to_expiration')
        
        # Add percentage of total GEX
        total_gex = exp_aggregation['total_gex'].sum()
        if total_gex != 0:
            exp_aggregation['gex_percentage'] = exp_aggregation['total_gex'] / total_gex * 100
        else:
            exp_aggregation['gex_percentage'] = 0
            
        return exp_aggregation
    
    def identify_gex_clusters(self, 
                            strike_gex,
                            underlying_price) :
        """
        Identify clusters of significant GEX around key price levels.
        
        Argsike_gex: DataFrame with GEX by strike
            underlying_price: Current underlying price
            
        Returns of GEX cluster information
        """
        if strike_gex.empty:
            return []
            
        # Filter for significant GEX levels
        significant_gex = strike_gex[
            abs(strike_gex['total_gex']) >= self.significant_gex_threshold
        ].copy()
        
        if significant_gex.empty:
            return []
            
        significant_gex = significant_gex.sort_values('strike')
        
        clusters = []
        current_cluster = []
        cluster_threshold_abs = underlying_price * self.clustering_threshold
        
        for _, row in significant_gex.iterrows():
            if not current_cluster:
                # Start new cluster
                current_cluster = [row]
            else:
                # Check if this strike is close to the last strike in cluster
                last_strike = current_cluster[-1]['strike']
                if abs(row['strike'] - last_strike) <= cluster_threshold_abs:
                    # Add to current cluster
                    current_cluster.append(row)
                else:
                    # Close current cluster and start new one
                    if len(current_cluster) > 0:
                        clusters.append(self._analyze_cluster(current_cluster, underlying_price))
                    current_cluster = [row]
        
        # Don't forget the last cluster
        if len(current_cluster) > 0:
            clusters.append(self._analyze_cluster(current_cluster, underlying_price))
        
        # Sort clusters by significance
        clusters.sort(key=lambda x: x['significance_score'], reverse=True)
        
        return clusters
    
    def _analyze_cluster(self, cluster_rows, underlying_price) :
        """
        Analyze a cluster of GEX levels.
        
        Args:
            cluster_rows of DataFrame rows in the cluster
            underlying_price: Current underlying price
            
        Returnsionary with cluster analysis
        """
        if not cluster_rows:
            return {}
            
        strikes = [row['strike'] for row in cluster_rows]
        gex_values = [row['total_gex'] for row in cluster_rows]
        oi_values = [row['total_oi'] for row in cluster_rows]
        
        cluster_center = np.mean(strikes)
        total_gex = sum(gex_values)
        total_oi = sum(oi_values)
        
        # Determine cluster type
        if total_gex > 0:
            cluster_type = "support" if cluster_center < underlying_price else "resistance"
            gex_direction = "positive"
        else:
            cluster_type = "resistance" if cluster_center < underlying_price else "support"
            gex_direction = "negative"
        
        # Calculate significance metrics
        distance_from_price = abs(cluster_center - underlying_price)
        distance_pct = distance_from_price / underlying_price
        gex_magnitude = abs(total_gex)
        
        # Significance score based on GEX magnitude and proximity
        proximity_score = max(0, 1 - distance_pct / 0.10)  # Full score within 10%
        magnitude_score = min(gex_magnitude / self.significant_gex_threshold, 10.0)
        significance_score = proximity_score * magnitude_score
        
        return {
            'cluster_center': cluster_center,
            'strike_range': (min(strikes), max(strikes)),
            'total_gex': total_gex,
            'total_oi': total_oi,
            'contract_count': len(cluster_rows),
            'cluster_type': cluster_type,
            'gex_direction': gex_direction,
            'distance_from_price': distance_from_price,
            'distance_pct': distance_pct,
            'proximity_score': proximity_score,
            'magnitude_score': magnitude_score,
            'significance_score': significance_score,
            'strikes': strikes,
            'underlying_price': underlying_price
        }
    
    def identify_key_levels(self, 
                          strike_gex,
                          underlying_price,
                          max_levels = 10) :
        """
        Identify key support and resistance levels from GEX data.
        
        Argsike_gex: DataFrame with GEX by strike
            underlying_price: Current underlying price
            max_levels: Maximum number of levels to return
            
        Returnsionary with key support and resistance levels
        """
        if strike_gex.empty:
            return {'support_levels': [], 'resistance_levels': []}
            
        # Identify GEX clusters
        clusters = self.identify_gex_clusters(strike_gex, underlying_price)
        
        # Separate into support and resistance
        support_clusters = [c for c in clusters if c['cluster_type'] == 'support']
        resistance_clusters = [c for c in clusters if c['cluster_type'] == 'resistance']
        
        # Select top levels by significance
        top_support = sorted(support_clusters, key=lambda x: x['significance_score'], reverse=True)[:max_levels//2]
        top_resistance = sorted(resistance_clusters, key=lambda x: x['significance_score'], reverse=True)[:max_levels//2]
        
        return {
            'support_levels': top_support,
            'resistance_levels': top_resistance,
            'all_clusters': clusters,
            'analysis_timestamp': datetime.now()
        }
    
    def create_gex_profile_summary(self, 
                                 strike_gex,
                                 exp_aggregation,
                                 underlying_price) :
        """
        Create comprehensive GEX profile summary.
        
        Argsike_gex: GEX aggregated by strike
            exp_aggregation: GEX aggregated by expiration
            underlying_price: Current underlying price
            
        Returns:
            Comprehensive GEX profile dictionary
        """
        logger.info("Creating comprehensive GEX profile summary")
        
        # Calculate basic metrics
        total_gex = strike_gex['total_gex'].sum() if not strike_gex.empty else 0
        net_gex_magnitude = abs(total_gex)
        
        # Strike-level analysis
        if not strike_gex.empty:
            max_positive_gex = strike_gex['total_gex'].max()
            max_negative_gex = strike_gex['total_gex'].min()
            
            # Find strikes with maximum GEX
            max_pos_strike = strike_gex.loc[strike_gex['total_gex'].idxmax(), 'strike'] if max_positive_gex > 0 else None
            max_neg_strike = strike_gex.loc[strike_gex['total_gex'].idxmin(), 'strike'] if max_negative_gex < 0 else None
        else:
            max_positive_gex = max_negative_gex = 0
            max_pos_strike = max_neg_strike = None
        
        # Key levels analysis
        key_levels = self.identify_key_levels(strike_gex, underlying_price)
        
        # Expiration analysis
        if not exp_aggregation.empty:
            near_term_gex = exp_aggregation.head(3)['total_gex'].sum()  # Next 3 expirations
            total_exp_gex = exp_aggregation['total_gex'].sum()
            near_term_percentage = (near_term_gex / total_exp_gex * 100) if total_exp_gex != 0 else 0
        else:
            near_term_gex = 0
            near_term_percentage = 0
        
        # Market structure assessment
        structure_assessment = self._assess_market_structure(
            total_gex, key_levels, underlying_price
        )
        
        return {
            'total_net_gex': total_gex,
            'gex_magnitude': net_gex_magnitude,
            'max_positive_gex': max_positive_gex,
            'max_negative_gex': max_negative_gex,
            'max_positive_strike': max_pos_strike,
            'max_negative_strike': max_neg_strike,
            'near_term_gex': near_term_gex,
            'near_term_gex_percentage': near_term_percentage,
            'key_support_levels': key_levels['support_levels'],
            'key_resistance_levels': key_levels['resistance_levels'],
            'total_clusters': len(key_levels['all_clusters']),
            'structure_assessment': structure_assessment,
            'underlying_price': underlying_price,
            'analysis_timestamp': datetime.now()
        }
    
    def _assess_market_structure(self, 
                               total_gex,
                               key_levels,
                               underlying_price) :
        """
        Assess overall market structure based on GEX profile.
        
        Args:
            total_gex: Total net GEX
            key_levels: Key support/resistance levels
            underlying_price: Current underlying price
            
        Returns:
            Market structure assessment
        """
        # GEX regime
        if total_gex > 0:
            gex_regime = "positive_gex"
            regime_description = "Dealer long gamma - supportive environment"
        elif total_gex < 0:
            gex_regime = "negative_gex"
            regime_description = "Dealer short gamma - reactive environment"
        else:
            gex_regime = "neutral_gex"
            regime_description = "Neutral gamma positioning"
        
        # Support/resistance structure
        support_count = len(key_levels['support_levels'])
        resistance_count = len(key_levels['resistance_levels'])
        
        if support_count > resistance_count:
            sr_structure = "support_heavy"
        elif resistance_count > support_count:
            sr_structure = "resistance_heavy"
        else:
            sr_structure = "balanced"
        
        # Find nearest levels
        support_levels = key_levels['support_levels']
        resistance_levels = key_levels['resistance_levels']
        
        nearest_support = None
        nearest_resistance = None
        
        if support_levels:
            below_price = [s for s in support_levels if s['cluster_center'] < underlying_price]
            if below_price:
                nearest_support = max(below_price, key=lambda x: x['cluster_center'])
        
        if resistance_levels:
            above_price = [r for r in resistance_levels if r['cluster_center'] > underlying_price]
            if above_price:
                nearest_resistance = min(above_price, key=lambda x: x['cluster_center'])
        
        # Trading range assessment
        if nearest_support and nearest_resistance:
            range_size = nearest_resistance['cluster_center'] - nearest_support['cluster_center']
            range_pct = range_size / underlying_price
            
            if range_pct < 0.03:
                range_assessment = "tight_range"
            elif range_pct < 0.08:
                range_assessment = "normal_range"
            else:
                range_assessment = "wide_range"
        else:
            range_assessment = "undefined_range"
            range_size = None
            range_pct = None
        
        return {
            'gex_regime': gex_regime,
            'regime_description': regime_description,
            'sr_structure': sr_structure,
            'support_count': support_count,
            'resistance_count': resistance_count,
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'range_assessment': range_assessment,
            'range_size': range_size,
            'range_percentage': range_pct
        }