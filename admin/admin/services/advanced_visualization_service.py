"""
Advanced Visualization Service for DrumTracKAI Desktop Application
Integrates sophisticated web-style visualizations with desktop Qt widgets
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import seaborn as sns
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from PySide6.QtCore import QObject, Signal, QTimer, QThread, QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton, QComboBox
from PySide6.QtWebEngineWidgets import QWebEngineView
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import tempfile
import os

logger = logging.getLogger(__name__)

@dataclass
class VisualizationData:
    """Container for visualization data"""
    drum_type: str
    hits: List[Dict]
    groove_pattern: Dict
    tempo_profile: Dict
    timing_profile: Dict
    neural_entrainment: Dict
    bass_drum_sync: Dict
    style_features: Dict
    humanness_score: float
    kit_coherence: Dict
    tfr_features: Optional[Dict] = None

class AdvancedVisualizationService(QObject):
    """Advanced visualization service combining matplotlib, plotly, and web technologies"""
    
    visualization_updated = Signal(str, object)  # visualization_type, data
    error_occurred = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_data = None
        self.web_template_path = None
        self._setup_matplotlib_style()
        self._setup_plotly_config()
        
    def _setup_matplotlib_style(self):
        """Setup matplotlib with dark theme similar to web interface"""
        plt.style.use('dark_background')
        
        # Custom color palette matching web interface
        self.colors = {
            'primary': '#6366f1',
            'secondary': '#8b5cf6', 
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444',
            'accent': '#00ff88',
            'text': '#f9fafb',
            'background': '#1f2937'
        }
        
        # Set default colors
        plt.rcParams.update({
            'figure.facecolor': self.colors['background'],
            'axes.facecolor': self.colors['background'],
            'axes.edgecolor': '#374151',
            'axes.labelcolor': self.colors['text'],
            'text.color': self.colors['text'],
            'xtick.color': self.colors['text'],
            'ytick.color': self.colors['text'],
            'grid.color': '#374151',
            'grid.alpha': 0.3
        })
        
    def _setup_plotly_config(self):
        """Setup plotly with dark theme"""
        self.plotly_template = {
            'layout': {
                'paper_bgcolor': self.colors['background'],
                'plot_bgcolor': self.colors['background'],
                'font': {'color': self.colors['text']},
                'colorway': [self.colors['primary'], self.colors['secondary'], 
                           self.colors['success'], self.colors['warning'], 
                           self.colors['danger'], self.colors['accent']],
                'xaxis': {
                    'gridcolor': '#374151',
                    'linecolor': '#374151',
                    'tickcolor': self.colors['text']
                },
                'yaxis': {
                    'gridcolor': '#374151', 
                    'linecolor': '#374151',
                    'tickcolor': self.colors['text']
                }
            }
        }

    def create_groove_radar_chart(self, data: VisualizationData) -> Figure:
        """Create advanced groove radar chart with matplotlib"""
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection='polar'))
        fig.patch.set_facecolor(self.colors['background'])
        
        # Extract groove data
        groove = data.groove_pattern
        
        # Radar chart data
        categories = ['Timing\nVariance', 'Velocity\nVariance', 'Ghost\nNotes', 
                     'Syncopation', 'Coherence', 'Bass Sync', 'Complexity']
        values = [
            groove.get('timing_variance', 0) * 100,
            groove.get('velocity_variance', 0) * 100, 
            groove.get('ghost_note_ratio', 0) * 100,
            groove.get('syncopation_score', 0) * 100,
            groove.get('groove_coherence', 0) * 100,
            groove.get('bass_sync_average', 0) * 100,
            groove.get('rhythmic_complexity', 0) * 100
        ]
        
        # Close the radar chart
        values += values[:1]
        
        # Angles for each category
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        # Plot
        ax.plot(angles, values, 'o-', linewidth=2, color=self.colors['accent'], 
                markersize=8, markerfacecolor=self.colors['primary'])
        ax.fill(angles, values, alpha=0.25, color=self.colors['accent'])
        
        # Customize
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=12, color=self.colors['text'])
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], 
                          fontsize=10, color=self.colors['text'])
        ax.grid(True, alpha=0.3)
        ax.set_facecolor(self.colors['background'])
        
        plt.title(f'Groove Characteristics - {data.drum_type.title()}', 
                 fontsize=16, color=self.colors['text'], pad=20)
        
        return fig

    def create_neural_entrainment_chart(self, data: VisualizationData) -> Figure:
        """Create neural entrainment visualization"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        fig.patch.set_facecolor(self.colors['background'])
        
        neural = data.neural_entrainment
        
        # Brainwave frequency bands
        bands = ['Delta\n(0.5-4 Hz)', 'Theta\n(4-8 Hz)', 'Alpha\n(8-13 Hz)', 
                'Beta\n(13-30 Hz)', 'Gamma\n(30-100 Hz)']
        values = [neural.get('delta', 0), neural.get('theta', 0), 
                 neural.get('alpha', 0), neural.get('beta', 0), neural.get('gamma', 0)]
        
        # Bar chart for brainwave alignment
        bars = ax1.bar(bands, values, color=[self.colors['primary'], self.colors['secondary'],
                                           self.colors['success'], self.colors['warning'], 
                                           self.colors['danger']], alpha=0.8)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{value:.2f}', ha='center', va='bottom', 
                    color=self.colors['text'], fontweight='bold')
        
        ax1.set_ylabel('Entrainment Strength', color=self.colors['text'])
        ax1.set_title('Neural Entrainment Profile', color=self.colors['text'], fontsize=14)
        ax1.set_ylim(0, 1.0)
        ax1.grid(True, alpha=0.3)
        ax1.set_facecolor(self.colors['background'])
        
        # Flow state compatibility visualization
        flow_metrics = ['Groove Induction', 'Phase Coherence', 'Tension-Release', 
                       'Predictability', 'Flow Compatibility']
        flow_values = [neural.get('groove_induction', 0.5), neural.get('phase_coherence', 0.7),
                      neural.get('tension_release', 0.6), neural.get('predictability', 0.8),
                      neural.get('flow_compatibility', 0.75)]
        
        # Horizontal bar chart for flow state
        bars2 = ax2.barh(flow_metrics, flow_values, 
                        color=self.colors['accent'], alpha=0.7)
        
        for bar, value in zip(bars2, flow_values):
            width = bar.get_width()
            ax2.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                    f'{value:.2f}', ha='left', va='center',
                    color=self.colors['text'], fontweight='bold')
        
        ax2.set_xlabel('Compatibility Score', color=self.colors['text'])
        ax2.set_title('Flow State Compatibility', color=self.colors['text'], fontsize=14)
        ax2.set_xlim(0, 1.0)
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.set_facecolor(self.colors['background'])
        
        plt.tight_layout()
        return fig

    def create_micro_timing_visualization(self, data: VisualizationData) -> Figure:
        """Create micro-timing analysis with sub-millisecond precision"""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))
        fig.patch.set_facecolor(self.colors['background'])
        
        # Extract timing data from hits
        hits = data.hits
        if not hits:
            return fig
            
        timestamps = [hit.get('timestamp', 0) for hit in hits]
        deviations = [hit.get('micro_timing_deviation', 0) for hit in hits]
        velocities = [hit.get('velocity', 0.5) for hit in hits]
        
        # 1. Micro-timing deviation over time
        scatter = ax1.scatter(timestamps, deviations, c=velocities, 
                            cmap='plasma', s=60, alpha=0.8, edgecolors='white', linewidth=0.5)
        
        # Add trend line
        if len(timestamps) > 1:
            z = np.polyfit(timestamps, deviations, 1)
            p = np.poly1d(z)
            ax1.plot(timestamps, p(timestamps), '--', color=self.colors['accent'], 
                    linewidth=2, alpha=0.8, label=f'Trend: {z[0]:.3f}ms/s')
            ax1.legend()
        
        ax1.axhline(y=0, color=self.colors['text'], linestyle='-', alpha=0.5)
        ax1.set_ylabel('Timing Deviation (ms)', color=self.colors['text'])
        ax1.set_title('Micro-Timing Analysis (Sub-millisecond Precision)', 
                     color=self.colors['text'], fontsize=14)
        ax1.grid(True, alpha=0.3)
        ax1.set_facecolor(self.colors['background'])
        
        # Add colorbar for velocity
        cbar = plt.colorbar(scatter, ax=ax1)
        cbar.set_label('Velocity', color=self.colors['text'])
        
        # 2. Timing deviation histogram
        ax2.hist(deviations, bins=30, alpha=0.7, color=self.colors['primary'], 
                edgecolor=self.colors['text'], linewidth=0.5)
        
        # Add statistics
        mean_dev = np.mean(deviations)
        std_dev = np.std(deviations)
        ax2.axvline(mean_dev, color=self.colors['accent'], linestyle='--', 
                   linewidth=2, label=f'Mean: {mean_dev:.2f}ms')
        ax2.axvline(mean_dev + std_dev, color=self.colors['warning'], 
                   linestyle=':', linewidth=2, label=f'+1σ: {mean_dev + std_dev:.2f}ms')
        ax2.axvline(mean_dev - std_dev, color=self.colors['warning'], 
                   linestyle=':', linewidth=2, label=f'-1σ: {mean_dev - std_dev:.2f}ms')
        
        ax2.set_xlabel('Timing Deviation (ms)', color=self.colors['text'])
        ax2.set_ylabel('Frequency', color=self.colors['text'])
        ax2.set_title('Timing Deviation Distribution', color=self.colors['text'], fontsize=14)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_facecolor(self.colors['background'])
        
        # 3. Groove consistency over time (rolling statistics)
        if len(deviations) > 10:
            window_size = min(10, len(deviations) // 3)
            rolling_std = []
            rolling_mean = []
            rolling_times = []
            
            for i in range(window_size, len(deviations)):
                window = deviations[i-window_size:i]
                rolling_std.append(np.std(window))
                rolling_mean.append(np.mean(window))
                rolling_times.append(timestamps[i])
            
            ax3.plot(rolling_times, rolling_std, color=self.colors['danger'], 
                    linewidth=2, label='Rolling Std Dev', marker='o', markersize=4)
            ax3.plot(rolling_times, np.abs(rolling_mean), color=self.colors['success'], 
                    linewidth=2, label='Rolling |Mean|', marker='s', markersize=4)
            
            ax3.set_xlabel('Time (s)', color=self.colors['text'])
            ax3.set_ylabel('Timing Consistency (ms)', color=self.colors['text'])
            ax3.set_title('Groove Consistency Over Time', color=self.colors['text'], fontsize=14)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            ax3.set_facecolor(self.colors['background'])
        
        plt.tight_layout()
        return fig

    def create_humanness_gauge(self, data: VisualizationData) -> Figure:
        """Create humanness score gauge visualization"""
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        fig.patch.set_facecolor(self.colors['background'])
        
        # Gauge parameters
        humanness = data.humanness_score
        
        # Create gauge background
        theta = np.linspace(0, np.pi, 100)
        r = np.ones_like(theta)
        
        # Color segments for different ranges
        colors = ['#ef4444', '#f59e0b', '#10b981']  # Red, Yellow, Green
        segments = [0.33, 0.66, 1.0]
        
        for i, (color, segment) in enumerate(zip(colors, segments)):
            start_angle = i * np.pi / 3
            end_angle = segment * np.pi
            segment_theta = np.linspace(start_angle, end_angle, 50)
            segment_r = np.ones_like(segment_theta)
            ax.fill_between(segment_theta, 0.8, 1.0, color=color, alpha=0.3)
        
        # Humanness needle
        needle_angle = humanness * np.pi
        ax.plot([needle_angle, needle_angle], [0, 0.9], 
               color=self.colors['accent'], linewidth=4)
        ax.plot(needle_angle, 0.9, 'o', color=self.colors['accent'], markersize=10)
        
        # Center circle
        center_circle = plt.Circle((0, 0), 0.1, color=self.colors['text'], 
                                 transform=ax.transData._b)
        ax.add_patch(center_circle)
        
        # Labels
        ax.text(0, -0.3, f'{humanness:.1%}', ha='center', va='center',
               fontsize=24, fontweight='bold', color=self.colors['text'])
        ax.text(0, -0.5, 'Humanness Score', ha='center', va='center',
               fontsize=16, color=self.colors['text'])
        
        # Remove axes
        ax.set_ylim(0, 1)
        ax.set_xlim(0, np.pi)
        ax.set_xticks([0, np.pi/3, 2*np.pi/3, np.pi])
        ax.set_xticklabels(['0%', '33%', '67%', '100%'], color=self.colors['text'])
        ax.set_yticks([])
        ax.grid(False)
        ax.set_facecolor(self.colors['background'])
        
        plt.title('Drummer Humanness Analysis', fontsize=18, color=self.colors['text'], pad=20)
        
        return fig

    def create_interactive_plotly_dashboard(self, data: VisualizationData) -> str:
        """Create interactive Plotly dashboard and return HTML"""
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=('Groove Radar', 'Neural Entrainment', 
                          'Micro-Timing', 'Tempo Analysis',
                          'Bass Synchronization', 'Kit Coherence'),
            specs=[[{"type": "polar"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # 1. Groove Radar (Polar plot)
        groove = data.groove_pattern
        categories = ['Timing Variance', 'Velocity Variance', 'Ghost Notes', 
                     'Syncopation', 'Coherence', 'Bass Sync', 'Complexity']
        values = [
            groove.get('timing_variance', 0) * 100,
            groove.get('velocity_variance', 0) * 100,
            groove.get('ghost_note_ratio', 0) * 100,
            groove.get('syncopation_score', 0) * 100,
            groove.get('groove_coherence', 0) * 100,
            groove.get('bass_sync_average', 0) * 100,
            groove.get('rhythmic_complexity', 0) * 100
        ]
        
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],  # Close the shape
                theta=categories + [categories[0]],
                fill='toself',
                name='Groove Profile',
                line_color='#00ff88'
            ),
            row=1, col=1
        )
        
        # 2. Neural Entrainment
        neural = data.neural_entrainment
        bands = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
        neural_values = [neural.get('delta', 0), neural.get('theta', 0),
                        neural.get('alpha', 0), neural.get('beta', 0), 
                        neural.get('gamma', 0)]
        
        fig.add_trace(
            go.Bar(x=bands, y=neural_values, name='Brainwave Alignment',
                  marker_color=['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444']),
            row=1, col=2
        )
        
        # 3. Micro-Timing
        hits = data.hits
        if hits:
            timestamps = [hit.get('timestamp', 0) for hit in hits]
            deviations = [hit.get('micro_timing_deviation', 0) for hit in hits]
            velocities = [hit.get('velocity', 0.5) for hit in hits]
            
            fig.add_trace(
                go.Scatter(x=timestamps, y=deviations, mode='markers',
                          marker=dict(size=8, color=velocities, colorscale='Plasma',
                                    showscale=True, colorbar=dict(title="Velocity")),
                          name='Timing Deviations'),
                row=2, col=1
            )
        
        # 4. Tempo Analysis
        tempo = data.tempo_profile
        if 'tempo_curve' in tempo and tempo['tempo_curve']:
            tempo_times = list(range(len(tempo['tempo_curve'])))
            fig.add_trace(
                go.Scatter(x=tempo_times, y=tempo['tempo_curve'],
                          mode='lines+markers', name='Tempo Curve',
                          line=dict(color='#6366f1', width=2)),
                row=2, col=2
            )
        
        # 5. Bass Synchronization
        bass_sync = data.bass_drum_sync
        sync_metrics = ['Lock Ratio', 'Sync Stability', 'Push-Pull Relationship']
        sync_values = [bass_sync.get('lock_ratio', 0), 
                      bass_sync.get('sync_stability', 0),
                      abs(bass_sync.get('push_pull_relationship', 0)) / 10]  # Normalize
        
        fig.add_trace(
            go.Bar(x=sync_metrics, y=sync_values, name='Bass Sync',
                  marker_color='#8b5cf6'),
            row=3, col=1
        )
        
        # 6. Kit Coherence
        coherence = data.kit_coherence
        coherence_metrics = list(coherence.keys())
        coherence_values = list(coherence.values())
        
        fig.add_trace(
            go.Bar(x=coherence_metrics, y=coherence_values, name='Kit Coherence',
                  marker_color='#10b981'),
            row=3, col=2
        )
        
        # Update layout with dark theme
        fig.update_layout(
            template='plotly_dark',
            title=f'Advanced Drummer Analysis - {data.drum_type.title()}',
            height=1200,
            showlegend=False,
            font=dict(color='#f9fafb'),
            paper_bgcolor='#1f2937',
            plot_bgcolor='#1f2937'
        )
        
        # Generate HTML
        html_content = pyo.plot(fig, output_type='div', include_plotlyjs=True)
        
        # Wrap in full HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DrumTracKAI Advanced Analysis</title>
            <style>
                body {{ 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #1f2937; 
                    color: #f9fafb;
                    font-family: 'Inter', sans-serif;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return full_html

    def create_web_visualization_widget(self, data: VisualizationData) -> QWidget:
        """Create a Qt widget containing web-based visualizations"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Drum selector
        drum_selector = QComboBox()
        drum_selector.addItems(['kick', 'snare', 'hihat', 'crash', 'ride', 'toms'])
        drum_selector.setCurrentText(data.drum_type)
        
        # View mode selector
        view_selector = QComboBox()
        view_selector.addItems(['Overview', 'Timing Analysis', 'Neural Entrainment', 
                               'Interactive Dashboard'])
        
        controls_layout.addWidget(QLabel("Drum:"))
        controls_layout.addWidget(drum_selector)
        controls_layout.addWidget(QLabel("View:"))
        controls_layout.addWidget(view_selector)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Web view for interactive content
        web_view = QWebEngineView()
        
        # Generate initial content
        html_content = self.create_interactive_plotly_dashboard(data)
        
        # Save to temp file and load
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_path = f.name
        
        web_view.load(QUrl.fromLocalFile(temp_path))
        layout.addWidget(web_view)
        
        # Store temp path for cleanup
        widget.temp_path = temp_path
        
        return widget

    def update_visualization(self, data: VisualizationData):
        """Update visualization with new data"""
        self.current_data = data
        self.visualization_updated.emit("data_updated", data)
        
    def export_analysis(self, data: VisualizationData, export_path: str, format: str = 'html'):
        """Export analysis to file"""
        try:
            if format == 'html':
                html_content = self.create_interactive_plotly_dashboard(data)
                with open(export_path, 'w') as f:
                    f.write(html_content)
            elif format == 'json':
                # Export raw data as JSON
                export_data = {
                    'drum_type': data.drum_type,
                    'groove_pattern': data.groove_pattern,
                    'tempo_profile': data.tempo_profile,
                    'timing_profile': data.timing_profile,
                    'neural_entrainment': data.neural_entrainment,
                    'bass_drum_sync': data.bass_drum_sync,
                    'humanness_score': data.humanness_score,
                    'kit_coherence': data.kit_coherence
                }
                with open(export_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
            
            logger.info(f"Analysis exported to {export_path}")
            
        except Exception as e:
            logger.error(f"Failed to export analysis: {str(e)}")
            self.error_occurred.emit(f"Export failed: {str(e)}")
