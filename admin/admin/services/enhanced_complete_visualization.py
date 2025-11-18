"""
Enhanced Complete Visualization Service
Integrates with DrumTracKAI Complete System for comprehensive analysis visualization
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedCompleteVisualization:
    """Enhanced visualization service for DrumTracKAI Complete System results"""
    
    def __init__(self):
        # Set up matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        self.figure_size = (15, 10)
        
    def create_complete_analysis_visualization(self, analysis_data: Dict) -> Figure:
        """Create comprehensive visualization from complete analysis data"""
        try:
            fig = Figure(figsize=self.figure_size, facecolor='white')
            
            # Create subplot layout (2x3 grid)
            gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
            
            # 1. Tempo Analysis (top left)
            ax1 = fig.add_subplot(gs[0, 0])
            self._plot_tempo_analysis(ax1, analysis_data)
            
            # 2. Hit Timeline (top middle)
            ax2 = fig.add_subplot(gs[0, 1])
            self._plot_hit_timeline(ax2, analysis_data)
            
            # 3. Style Radar Chart (top right)
            ax3 = fig.add_subplot(gs[0, 2], projection='polar')
            self._plot_style_radar(ax3, analysis_data)
            
            # 4. Neural Entrainment (middle left)
            ax4 = fig.add_subplot(gs[1, 0])
            self._plot_neural_entrainment(ax4, analysis_data)
            
            # 5. Rhythm Hierarchy (middle middle)
            ax5 = fig.add_subplot(gs[1, 1])
            self._plot_rhythm_hierarchy(ax5, analysis_data)
            
            # 6. Groove Metrics (middle right)
            ax6 = fig.add_subplot(gs[1, 2])
            self._plot_groove_metrics(ax6, analysis_data)
            
            # 7. Micro-timing Analysis (bottom span)
            ax7 = fig.add_subplot(gs[2, :])
            self._plot_micro_timing_analysis(ax7, analysis_data)
            
            # Add title
            drummer_id = analysis_data.get('drummer_id', 'Unknown')
            track_name = analysis_data.get('track_name', 'Unknown')
            fig.suptitle(f'Complete Analysis: {drummer_id} - {track_name}', 
                        fontsize=16, fontweight='bold')
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating complete visualization: {e}")
            # Return empty figure on error
            fig = Figure(figsize=self.figure_size)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f'Visualization Error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
            return fig
    
    def _plot_tempo_analysis(self, ax, analysis_data):
        """Plot tempo curve and stability"""
        try:
            viz_data = analysis_data.get('visualization_data', {})
            tempo_data = viz_data.get('tempo_curve', {})
            
            times = tempo_data.get('times', [])
            tempos = tempo_data.get('tempos', [])
            
            if times and tempos:
                ax.plot(times, tempos, 'b-', linewidth=2, label='Tempo Curve')
                ax.axhline(y=np.mean(tempos), color='r', linestyle='--', 
                          label=f'Average: {np.mean(tempos):.1f} BPM')
                ax.fill_between(times, tempos, alpha=0.3)
            
            tempo_profile = analysis_data.get('tempo_profile', {})
            stability = tempo_profile.get('tempo_stability', 0)
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Tempo (BPM)')
            ax.set_title(f'Tempo Analysis (Stability: {stability:.2f})')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Tempo plot error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_hit_timeline(self, ax, analysis_data):
        """Plot hit timeline with velocities"""
        try:
            viz_data = analysis_data.get('visualization_data', {})
            hit_data = viz_data.get('hit_timeline', {})
            
            times = hit_data.get('times', [])
            velocities = hit_data.get('velocities', [])
            
            if times and velocities:
                # Create scatter plot with velocity as color
                scatter = ax.scatter(times, velocities, c=velocities, 
                                   cmap='viridis', s=50, alpha=0.7)
                
                # Add colorbar
                plt.colorbar(scatter, ax=ax, label='Velocity')
                
                # Add trend line
                if len(times) > 1:
                    z = np.polyfit(times, velocities, 1)
                    p = np.poly1d(z)
                    ax.plot(times, p(times), "r--", alpha=0.8, label='Trend')
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Velocity')
            ax.set_title('Hit Timeline')
            ax.grid(True, alpha=0.3)
            if len(times) > 1:
                ax.legend()
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Hit timeline error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_style_radar(self, ax, analysis_data):
        """Plot style characteristics on radar chart"""
        try:
            viz_data = analysis_data.get('visualization_data', {})
            radar_data = viz_data.get('style_radar', {})
            
            categories = radar_data.get('categories', ['Complexity', 'Syncopation', 'Dynamics', 'Precision', 'Groove', 'Flow'])
            values = radar_data.get('values', [0.5] * len(categories))
            
            # Ensure values are normalized to 0-1
            values = [max(0, min(1, v)) for v in values]
            
            # Number of variables
            num_vars = len(categories)
            
            # Compute angle for each axis
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            values += values[:1]  # Complete the circle
            angles += angles[:1]
            
            # Plot
            ax.plot(angles, values, 'o-', linewidth=2, color='blue')
            ax.fill(angles, values, alpha=0.25, color='blue')
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_thetagrids(np.degrees(angles[:-1]), categories)
            ax.set_ylim(0, 1)
            ax.set_title('Style Profile', y=1.08)
            ax.grid(True)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Radar plot error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_neural_entrainment(self, ax, analysis_data):
        """Plot neural entrainment spectrum"""
        try:
            viz_data = analysis_data.get('visualization_data', {})
            entrainment_data = viz_data.get('entrainment_spectrum', {})
            
            frequencies = entrainment_data.get('frequencies', ['delta', 'theta', 'alpha', 'beta', 'gamma'])
            amplitudes = entrainment_data.get('amplitudes', [0.2, 0.3, 0.4, 0.3, 0.1])
            
            # Create bar plot
            bars = ax.bar(frequencies, amplitudes, color=['red', 'orange', 'green', 'blue', 'purple'])
            
            # Add value labels on bars
            for bar, amp in zip(bars, amplitudes):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{amp:.2f}', ha='center', va='bottom')
            
            ax.set_ylabel('Alignment Strength')
            ax.set_title('Neural Entrainment Profile')
            ax.set_ylim(0, max(amplitudes) * 1.2)
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Entrainment plot error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_rhythm_hierarchy(self, ax, analysis_data):
        """Plot rhythm hierarchy visualization - AUTHENTIC DATA ONLY"""
        try:
            rhythm_data = analysis_data.get('rhythm_hierarchy', {})
            
            # Check if we have REAL rhythm hierarchy data
            required_keys = ['complexity_score', 'syncopation_score', 'hierarchical_depth']
            if rhythm_data and all(key in rhythm_data for key in required_keys):
                complexity = rhythm_data['complexity_score']
                syncopation = rhythm_data['syncopation_score']
                hierarchical_depth = rhythm_data['hierarchical_depth']
                
                # Verify values are not default/placeholder (0 could be real for some metrics)
                if complexity > 0 or syncopation > 0 or hierarchical_depth > 1:
                    # Create hierarchy visualization with REAL data
                    metrics = ['Complexity', 'Syncopation', 'Depth']
                    values = [complexity, syncopation, min(hierarchical_depth / 5.0, 1.0)]  # Normalize depth
                    
                    bars = ax.barh(metrics, values, color=['coral', 'lightblue', 'lightgreen'])
                    
                    # Add value labels with authenticity indicator
                    for i, (bar, value) in enumerate(zip(bars, values)):
                        width = bar.get_width()
                        ax.text(width + 0.01, bar.get_y() + bar.get_height()/2,
                               f'{value:.3f}', ha='left', va='center', fontsize=8)
                    
                    ax.set_xlim(0, 1)
                    ax.set_title('Rhythm Hierarchy (AUTHENTIC)', fontsize=10, color='darkgreen')
                    ax.grid(True, alpha=0.3)
                    
                    # Add authenticity indicator
                    ax.text(0.02, 0.02, ' REAL ANALYSIS', transform=ax.transAxes, 
                           fontsize=6, color='green', weight='bold')
                else:
                    # All values are zero - likely no real analysis
                    ax.text(0.5, 0.5, 'RHYTHM ANALYSIS FAILED\n(All values zero)', 
                           ha='center', va='center', transform=ax.transAxes,
                           fontsize=10, color='red', weight='bold')
                    ax.set_title('Rhythm Hierarchy (NO DATA)', color='red')
            else:
                # Missing required data
                ax.text(0.5, 0.5, 'RHYTHM HIERARCHY\nDATA MISSING', 
                       ha='center', va='center', transform=ax.transAxes,
                       fontsize=10, color='red', weight='bold')
                ax.set_title('Rhythm Hierarchy (UNAVAILABLE)', color='red')
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Hierarchy plot error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_groove_metrics(self, ax, analysis_data):
        """Plot groove metrics - AUTHENTIC DATA ONLY"""
        try:
            groove_data = analysis_data.get('groove_metrics', {})
            
            # Check if we have REAL groove metrics data
            required_keys = ['timing_tightness', 'dynamic_consistency', 'attack_consistency', 'groove_depth']
            if groove_data and all(key in groove_data for key in required_keys):
                values = [
                    groove_data['timing_tightness'],
                    groove_data['dynamic_consistency'],
                    groove_data['attack_consistency'],
                    groove_data['groove_depth']
                ]
                
                # Verify we have non-zero values (some could legitimately be 0, but not all)
                if any(v > 0 for v in values):
                    metrics = ['Timing\nTightness', 'Dynamic\nConsistency', 'Attack\nConsistency', 'Groove\nDepth']
            
            # Create circular plot
            angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False)
            
            # Create bar plot in circular arrangement
            bars = ax.bar(angles, values, width=0.8, alpha=0.7)
            
            # Customize
            ax.set_theta_zero_location('N')
            ax.set_theta_direction(-1)
            ax.set_thetagrids(np.degrees(angles), metrics)
            ax.set_ylim(0, 1)
            ax.set_title('Groove Metrics', y=1.08)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Groove plot error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_micro_timing_analysis(self, ax, analysis_data):
        """Plot micro-timing deviations"""
        try:
            viz_data = analysis_data.get('visualization_data', {})
            hit_data = viz_data.get('hit_timeline', {})
            
            times = hit_data.get('times', [])
            micro_timing = hit_data.get('micro_timing', [])
            
            if times and micro_timing:
                # Plot micro-timing deviations
                ax.plot(times, micro_timing, 'g-', linewidth=1, alpha=0.7, label='Micro-timing')
                ax.scatter(times, micro_timing, c='green', s=30, alpha=0.8)
                
                # Add zero line
                ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
                
                # Add standard deviation bands
                if len(micro_timing) > 1:
                    std_dev = np.std(micro_timing)
                    ax.axhline(y=std_dev, color='red', linestyle='--', alpha=0.5, label=f'+1σ ({std_dev:.1f}ms)')
                    ax.axhline(y=-std_dev, color='red', linestyle='--', alpha=0.5, label=f'-1σ ({-std_dev:.1f}ms)')
                    ax.fill_between(times, -std_dev, std_dev, alpha=0.2, color='red')
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Micro-timing Deviation (ms)')
            ax.set_title('Micro-timing Analysis')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Micro-timing plot error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def create_drummer_comparison_visualization(self, drummer_analyses: List[Dict]) -> Figure:
        """Create comparison visualization for multiple drummers"""
        try:
            fig = Figure(figsize=(12, 8), facecolor='white')
            
            if not drummer_analyses:
                ax = fig.add_subplot(111)
                ax.text(0.5, 0.5, 'No drummer analyses available', 
                       ha='center', va='center', transform=ax.transAxes)
                return fig
            
            # Create comparison plots
            gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
            
            # 1. Tempo comparison
            ax1 = fig.add_subplot(gs[0, 0])
            self._plot_tempo_comparison(ax1, drummer_analyses)
            
            # 2. Groove metrics comparison
            ax2 = fig.add_subplot(gs[0, 1])
            self._plot_groove_comparison(ax2, drummer_analyses)
            
            # 3. Style characteristics comparison
            ax3 = fig.add_subplot(gs[1, 0])
            self._plot_style_comparison(ax3, drummer_analyses)
            
            # 4. Complexity vs Flow scatter
            ax4 = fig.add_subplot(gs[1, 1])
            self._plot_complexity_flow_scatter(ax4, drummer_analyses)
            
            fig.suptitle('Drummer Comparison Analysis', fontsize=16, fontweight='bold')
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating comparison visualization: {e}")
            fig = Figure(figsize=(12, 8))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f'Comparison Error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
            return fig
    
    def _plot_tempo_comparison(self, ax, drummer_analyses):
        """Compare tempo characteristics across drummers"""
        try:
            drummers = []
            tempos = []
            stabilities = []
            
            for analysis in drummer_analyses:
                drummer_id = analysis.get('drummer_id', 'Unknown')
                tempo_profile = analysis.get('tempo_profile', {})
                
                drummers.append(drummer_id)
                tempos.append(tempo_profile.get('average_tempo', 120))
                stabilities.append(tempo_profile.get('tempo_stability', 0.5))
            
            x = np.arange(len(drummers))
            width = 0.35
            
            ax.bar(x - width/2, tempos, width, label='Avg Tempo (BPM)', alpha=0.7)
            ax2 = ax.twinx()
            ax2.bar(x + width/2, stabilities, width, label='Stability', alpha=0.7, color='orange')
            
            ax.set_xlabel('Drummers')
            ax.set_ylabel('Tempo (BPM)', color='blue')
            ax2.set_ylabel('Stability', color='orange')
            ax.set_title('Tempo Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(drummers, rotation=45)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Tempo comparison error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_groove_comparison(self, ax, drummer_analyses):
        """Compare groove metrics across drummers"""
        try:
            drummers = []
            groove_scores = []
            
            for analysis in drummer_analyses:
                drummer_id = analysis.get('drummer_id', 'Unknown')
                groove_metrics = analysis.get('groove_metrics', {})
                
                drummers.append(drummer_id)
                groove_scores.append(groove_metrics.get('overall_groove_score', 0.5))
            
            bars = ax.bar(drummers, groove_scores, color='green', alpha=0.7)
            
            # Add value labels on bars
            for bar, score in zip(bars, groove_scores):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{score:.2f}', ha='center', va='bottom')
            
            ax.set_ylabel('Groove Score')
            ax.set_title('Groove Quality Comparison')
            ax.set_ylim(0, 1)
            plt.setp(ax.get_xticklabels(), rotation=45)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Groove comparison error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_style_comparison(self, ax, drummer_analyses):
        """Compare style characteristics"""
        try:
            drummers = []
            complexities = []
            syncopations = []
            
            for analysis in drummer_analyses:
                drummer_id = analysis.get('drummer_id', 'Unknown')
                rhythm_hierarchy = analysis.get('rhythm_hierarchy', {})
                
                drummers.append(drummer_id)
                complexities.append(rhythm_hierarchy.get('complexity_score', 0.5))
                syncopations.append(rhythm_hierarchy.get('syncopation_score', 0.5))
            
            x = np.arange(len(drummers))
            width = 0.35
            
            ax.bar(x - width/2, complexities, width, label='Complexity', alpha=0.7)
            ax.bar(x + width/2, syncopations, width, label='Syncopation', alpha=0.7)
            
            ax.set_xlabel('Drummers')
            ax.set_ylabel('Score')
            ax.set_title('Style Characteristics')
            ax.set_xticks(x)
            ax.set_xticklabels(drummers, rotation=45)
            ax.legend()
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Style comparison error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    def _plot_complexity_flow_scatter(self, ax, drummer_analyses):
        """Scatter plot of complexity vs flow compatibility"""
        try:
            complexities = []
            flow_compatibilities = []
            drummer_names = []
            
            for analysis in drummer_analyses:
                drummer_id = analysis.get('drummer_id', 'Unknown')
                rhythm_hierarchy = analysis.get('rhythm_hierarchy', {})
                neural_entrainment = analysis.get('neural_entrainment', {})
                
                complexities.append(rhythm_hierarchy.get('complexity_score', 0.5))
                flow_compatibilities.append(neural_entrainment.get('flow_state_compatibility', 0.5))
                drummer_names.append(drummer_id)
            
            scatter = ax.scatter(complexities, flow_compatibilities, s=100, alpha=0.7)
            
            # Add labels for each point
            for i, name in enumerate(drummer_names):
                ax.annotate(name, (complexities[i], flow_compatibilities[i]), 
                           xytext=(5, 5), textcoords='offset points')
            
            ax.set_xlabel('Complexity Score')
            ax.set_ylabel('Flow State Compatibility')
            ax.set_title('Complexity vs Flow State')
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Scatter plot error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)

# Global visualization service instance
_visualization_service = None

def get_enhanced_complete_visualization() -> EnhancedCompleteVisualization:
    """Get the global enhanced complete visualization service"""
    global _visualization_service
    if _visualization_service is None:
        _visualization_service = EnhancedCompleteVisualization()
    return _visualization_service
