"""Interactive HTML viewer for aerodeck data."""

import json
from pathlib import Path
from typing import Dict, Any
import webbrowser
from datetime import datetime
import numpy as np


class HTMLViewer:
    """Generate interactive HTML visualization of aerodeck data."""

    def __init__(self, aerodeck_path: Path):
        """
        Initialize HTML viewer.

        Args:
            aerodeck_path: Path to aerodeck JSON file
        """
        self.aerodeck_path = Path(aerodeck_path)
        with open(self.aerodeck_path, 'r') as f:
            self.data = json.load(f)

    def generate_html(self, output_path: Path = None, open_browser: bool = True) -> Path:
        """
        Generate interactive HTML page.

        Args:
            output_path: Path to save HTML file (default: same dir as JSON)
            open_browser: Whether to open in browser automatically

        Returns:
            Path to generated HTML file
        """
        if output_path is None:
            output_path = self.aerodeck_path.with_suffix('.html')

        html_content = self._build_html()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        if open_browser:
            webbrowser.open(f'file://{output_path.absolute()}')

        return output_path

    def _build_html(self) -> str:
        """Build complete HTML document."""
        metadata = self.data.get('metadata', {})
        reference = self.data.get('reference_geometry', {})
        mass = self.data.get('mass_properties', {})

        # Handle nested aerodynamics structure
        aero = self.data.get('aerodynamics', {})
        static_stab = aero.get('static_stability', {})
        dynamic_stab = aero.get('dynamic_stability', {})

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AeroDeck Viewer - {metadata.get('aircraft_name', 'Aircraft')}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px;
        }}

        .tabs {{
            display: flex;
            gap: 10px;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .tab {{
            padding: 15px 30px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1em;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }}

        .tab:hover {{
            background: #f5f5f5;
            color: #333;
        }}

        .tab.active {{
            color: #667eea;
            border-bottom-color: #667eea;
            font-weight: 600;
        }}

        .tab-content {{
            display: none;
            animation: fadeIn 0.3s;
        }}

        .tab-content.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}

        .card h3 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .metric {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }}

        .metric-label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}

        .metric-value {{
            color: #333;
            font-size: 1.5em;
            font-weight: 600;
        }}

        .metric-unit {{
            color: #999;
            font-size: 0.9em;
            margin-left: 5px;
        }}

        .plot-container {{
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            padding: 10px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{metadata.get('aircraft_name', 'Aircraft Analysis')}</h1>
            <p>Interactive Aerodynamic Deck Viewer</p>
            <p style="font-size: 0.9em; opacity: 0.8;">Generated: {metadata.get('generated_date', 'Unknown')}</p>
        </div>

        <div class="content">
            <div class="tabs">
                <button class="tab active" onclick="showTab('overview')">Overview</button>
                <button class="tab" onclick="showTab('geometry')">Geometry</button>
                <button class="tab" onclick="showTab('stability')">Stability</button>
                <button class="tab" onclick="showTab('control')">Control</button>
                <button class="tab" onclick="showTab('polars')">Polars</button>
            </div>

            <div id="overview" class="tab-content active">
                {self._build_overview_tab(metadata, reference, mass)}
            </div>

            <div id="geometry" class="tab-content">
                {self._build_geometry_tab(reference, mass)}
            </div>

            <div id="stability" class="tab-content">
                {self._build_stability_tab(static_stab, dynamic_stab)}
            </div>

            <div id="control" class="tab-content">
                {self._build_control_tab(aero)}
            </div>

            <div id="polars" class="tab-content">
                {self._build_polars_tab()}
            </div>
        </div>

        <div class="footer">
            Generated by nTop AeroDeck Generator • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>

    <script>
        function showTab(tabName) {{
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
            }});

            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}

        // Initialize plots
        {self._build_plot_scripts()}
    </script>
</body>
</html>"""

    def _build_overview_tab(self, metadata: Dict, reference: Dict, mass: Dict) -> str:
        """Build overview tab content."""
        # Extract reference geometry with correct key names
        S_ref_ft2 = reference.get('S_ref_ft2', reference.get('S_ref', 0))
        b_ref_ft = reference.get('b_ref_ft', reference.get('b_ref', 0))
        c_ref_ft = reference.get('c_ref_ft', reference.get('c_ref', 0))

        # Calculate aspect ratio
        aspect_ratio = (b_ref_ft ** 2 / S_ref_ft2) if S_ref_ft2 > 0 else 0

        return f"""
            <div class="card">
                <h3>Aircraft Summary</h3>
                <div class="grid">
                    <div class="metric">
                        <div class="metric-label">Aircraft Name</div>
                        <div class="metric-value">{metadata.get('aircraft_name', 'N/A')}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Version</div>
                        <div class="metric-value">{metadata.get('generator_version', metadata.get('version', 'N/A'))}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Reference Area</div>
                        <div class="metric-value">{S_ref_ft2:.2f}<span class="metric-unit">ft²</span></div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Wingspan</div>
                        <div class="metric-value">{b_ref_ft:.2f}<span class="metric-unit">ft</span></div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Mean Chord</div>
                        <div class="metric-value">{c_ref_ft:.2f}<span class="metric-unit">ft</span></div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Mass</div>
                        <div class="metric-value">{mass.get('mass_lbm', 0):.1f}<span class="metric-unit">lbm</span></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>Key Performance</h3>
                <div class="grid">
                    <div class="metric">
                        <div class="metric-label">Aspect Ratio</div>
                        <div class="metric-value">{aspect_ratio:.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Wing Loading</div>
                        <div class="metric-value">{(mass.get('mass_lbm', 0) / S_ref_ft2 if S_ref_ft2 > 0 else 0):.1f}<span class="metric-unit">lbm/ft²</span></div>
                    </div>
                </div>
            </div>
        """

    def _build_geometry_tab(self, reference: Dict, mass: Dict) -> str:
        """Build geometry tab content."""
        cg = mass.get('cg_ft', [0, 0, 0])
        inertia = mass.get('inertia_lbm_ft2', {})

        # Extract reference geometry with correct key names
        S_ref_ft2 = reference.get('S_ref_ft2', reference.get('S_ref', 0))
        b_ref_ft = reference.get('b_ref_ft', reference.get('b_ref', 0))
        c_ref_ft = reference.get('c_ref_ft', reference.get('c_ref', 0))

        # Calculate aspect ratio
        aspect_ratio = (b_ref_ft ** 2 / S_ref_ft2) if S_ref_ft2 > 0 else 0

        return f"""
            <div class="card">
                <h3>Reference Geometry</h3>
                <table>
                    <tr><th>Parameter</th><th>Value</th><th>Units</th></tr>
                    <tr><td>Wing Area (S<sub>ref</sub>)</td><td>{S_ref_ft2:.3f}</td><td>ft²</td></tr>
                    <tr><td>Wingspan (b<sub>ref</sub>)</td><td>{b_ref_ft:.3f}</td><td>ft</td></tr>
                    <tr><td>Mean Chord (c<sub>ref</sub>)</td><td>{c_ref_ft:.3f}</td><td>ft</td></tr>
                    <tr><td>Aspect Ratio</td><td>{aspect_ratio:.3f}</td><td>-</td></tr>
                </table>
            </div>

            <div class="card">
                <h3>Mass Properties</h3>
                <table>
                    <tr><th>Parameter</th><th>Value</th><th>Units</th></tr>
                    <tr><td>Mass</td><td>{mass.get('mass_lbm', 0):.2f}</td><td>lbm</td></tr>
                    <tr><td>CG x</td><td>{cg[0]:.3f}</td><td>ft</td></tr>
                    <tr><td>CG y</td><td>{cg[1]:.3f}</td><td>ft</td></tr>
                    <tr><td>CG z</td><td>{cg[2]:.3f}</td><td>ft</td></tr>
                    <tr><td>I<sub>xx</sub></td><td>{inertia.get('Ixx', 0):.2f}</td><td>lbm·ft²</td></tr>
                    <tr><td>I<sub>yy</sub></td><td>{inertia.get('Iyy', 0):.2f}</td><td>lbm·ft²</td></tr>
                    <tr><td>I<sub>zz</sub></td><td>{inertia.get('Izz', 0):.2f}</td><td>lbm·ft²</td></tr>
                </table>
            </div>
        """

    def _build_stability_tab(self, static: Dict, dynamic: Dict) -> str:
        """Build stability tab content."""
        # Extract nested structure
        longitudinal = static.get('longitudinal', {})
        lateral_directional = static.get('lateral_directional', {})
        pitch_rate = dynamic.get('pitch_rate', {})
        roll_rate = dynamic.get('roll_rate', {})
        yaw_rate = dynamic.get('yaw_rate', {})

        return f"""
            <div class="card">
                <h3>Static Stability Derivatives</h3>
                <div class="plot-container">
                    <div id="static-derivatives-plot"></div>
                </div>
                <table>
                    <tr><th>Derivative</th><th>Value</th><th>Units</th><th>Description</th></tr>
                    <tr><td>CL<sub>α</sub></td><td>{longitudinal.get('CL_alpha_per_rad', 0):.3f}</td><td>/rad</td><td>Lift curve slope</td></tr>
                    <tr><td>Cm<sub>α</sub></td><td>{longitudinal.get('Cm_alpha_per_rad', 0):.3f}</td><td>/rad</td><td>Pitch stability</td></tr>
                    <tr><td>Cn<sub>β</sub></td><td>{lateral_directional.get('Cn_beta_per_rad', 0):.3f}</td><td>/rad</td><td>Yaw stability</td></tr>
                    <tr><td>Cl<sub>β</sub></td><td>{lateral_directional.get('Cl_beta_per_rad', 0):.3f}</td><td>/rad</td><td>Dihedral effect</td></tr>
                </table>
            </div>

            <div class="card">
                <h3>Dynamic Stability Derivatives</h3>
                <div class="plot-container">
                    <div id="dynamic-derivatives-plot"></div>
                </div>
                <table>
                    <tr><th>Derivative</th><th>Value</th><th>Units</th><th>Description</th></tr>
                    <tr><td>CL<sub>q</sub></td><td>{pitch_rate.get('CL_q_per_rad', 0):.3f}</td><td>/rad</td><td>Pitch damping (lift)</td></tr>
                    <tr><td>Cm<sub>q</sub></td><td>{pitch_rate.get('Cm_q_per_rad', 0):.3f}</td><td>/rad</td><td>Pitch damping (moment)</td></tr>
                    <tr><td>Cl<sub>p</sub></td><td>{roll_rate.get('Cl_p_per_rad', 0):.3f}</td><td>/rad</td><td>Roll damping</td></tr>
                    <tr><td>Cn<sub>r</sub></td><td>{yaw_rate.get('Cn_r_per_rad', 0):.3f}</td><td>/rad</td><td>Yaw damping</td></tr>
                </table>
            </div>
        """

    def _build_control_tab(self, aero: Dict) -> str:
        """Build control effectiveness tab content."""
        # Extract control surfaces from array
        control_surfaces = aero.get('control_surfaces', [])

        # Find elevon and aileron controls
        elevon_control = None
        aileron_control = None
        for cs in control_surfaces:
            if cs.get('name') == 'Elevon':
                elevon_control = cs
            elif cs.get('name') == 'Aileron':
                aileron_control = cs

        # Get elevon effectiveness (convert from per-radian to per-degree)
        if elevon_control:
            elevon_eff = elevon_control.get('effectiveness', {})
            CL_de_per_deg = elevon_eff.get('CL_delta_per_rad', 0) * 180 / np.pi
            Cm_de_per_deg = elevon_eff.get('Cm_delta_per_rad', 0) * 180 / np.pi
        else:
            CL_de_per_deg = 0
            Cm_de_per_deg = 0

        # Get aileron effectiveness (convert from per-radian to per-degree)
        if aileron_control:
            aileron_eff = aileron_control.get('effectiveness', {})
            Cl_da_per_deg = aileron_eff.get('Cl_delta_per_rad', 0) * 180 / np.pi
            Cn_da_per_deg = aileron_eff.get('Cn_delta_per_rad', 0) * 180 / np.pi
        else:
            Cl_da_per_deg = 0
            Cn_da_per_deg = 0

        return f"""
            <div class="card">
                <h3>Elevon Control Effectiveness</h3>
                <div class="plot-container">
                    <div id="elevon-effectiveness-plot"></div>
                </div>
                <table>
                    <tr><th>Derivative</th><th>Value</th><th>Units</th><th>Description</th></tr>
                    <tr><td>CL<sub>δe</sub></td><td>{CL_de_per_deg:.4f}</td><td>/deg</td><td>Lift per elevon deflection</td></tr>
                    <tr><td>Cm<sub>δe</sub></td><td>{Cm_de_per_deg:.4f}</td><td>/deg</td><td>Pitch per elevon deflection</td></tr>
                </table>
            </div>

            <div class="card">
                <h3>Aileron Control Effectiveness</h3>
                <div class="plot-container">
                    <div id="aileron-effectiveness-plot"></div>
                </div>
                <table>
                    <tr><th>Derivative</th><th>Value</th><th>Units</th><th>Description</th></tr>
                    <tr><td>Cl<sub>δa</sub></td><td>{Cl_da_per_deg:.4f}</td><td>/deg</td><td>Roll per aileron deflection</td></tr>
                    <tr><td>Cn<sub>δa</sub></td><td>{Cn_da_per_deg:.4f}</td><td>/deg</td><td>Adverse yaw</td></tr>
                </table>
            </div>
        """

    def _build_polars_tab(self) -> str:
        """Build polars tab content."""
        return f"""
            <div class="card">
                <h3>Airfoil Polars</h3>
                <div class="plot-container">
                    <div id="polars-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Drag Polar</h3>
                <div class="plot-container">
                    <div id="drag-polar-plot"></div>
                </div>
            </div>
        """

    def _build_plot_scripts(self) -> str:
        """Build Plotly.js plotting scripts."""
        # Extract nested structure
        aero = self.data.get('aerodynamics', {})
        static_stab = aero.get('static_stability', {})
        dynamic_stab = aero.get('dynamic_stability', {})

        longitudinal = static_stab.get('longitudinal', {})
        lateral_directional = static_stab.get('lateral_directional', {})
        pitch_rate = dynamic_stab.get('pitch_rate', {})
        roll_rate = dynamic_stab.get('roll_rate', {})
        yaw_rate = dynamic_stab.get('yaw_rate', {})

        # Extract control surfaces
        control_surfaces = aero.get('control_surfaces', [])
        elevon_control = None
        aileron_control = None
        for cs in control_surfaces:
            if cs.get('name') == 'Elevon':
                elevon_control = cs
            elif cs.get('name') == 'Aileron':
                aileron_control = cs

        # Get control effectiveness (convert from per-radian to per-degree)
        if elevon_control:
            elevon_eff = elevon_control.get('effectiveness', {})
            Cm_de_per_deg = elevon_eff.get('Cm_delta_per_rad', 0) * 180 / np.pi
        else:
            Cm_de_per_deg = 0

        if aileron_control:
            aileron_eff = aileron_control.get('effectiveness', {})
            Cl_da_per_deg = aileron_eff.get('Cl_delta_per_rad', 0) * 180 / np.pi
        else:
            Cl_da_per_deg = 0

        return f"""
        // Static derivatives bar chart
        const staticData = [{{
            x: ['CL_α', 'Cm_α', 'Cn_β', 'Cl_β'],
            y: [{longitudinal.get('CL_alpha_per_rad', 0)}, {longitudinal.get('Cm_alpha_per_rad', 0)},
                {lateral_directional.get('Cn_beta_per_rad', 0)}, {lateral_directional.get('Cl_beta_per_rad', 0)}],
            type: 'bar',
            marker: {{ color: ['#667eea', '#764ba2', '#f093fb', '#f5576c'] }}
        }}];

        const staticLayout = {{
            title: 'Static Stability Derivatives',
            xaxis: {{ title: 'Derivative' }},
            yaxis: {{ title: 'Value (/rad)' }},
            height: 400
        }};

        Plotly.newPlot('static-derivatives-plot', staticData, staticLayout, {{responsive: true}});

        // Dynamic derivatives bar chart
        const dynamicData = [{{
            x: ['CL_q', 'Cm_q', 'Cl_p', 'Cn_r'],
            y: [{pitch_rate.get('CL_q_per_rad', 0)}, {pitch_rate.get('Cm_q_per_rad', 0)},
                {roll_rate.get('Cl_p_per_rad', 0)}, {yaw_rate.get('Cn_r_per_rad', 0)}],
            type: 'bar',
            marker: {{ color: ['#667eea', '#764ba2', '#f093fb', '#f5576c'] }}
        }}];

        const dynamicLayout = {{
            title: 'Dynamic Stability Derivatives',
            xaxis: {{ title: 'Derivative' }},
            yaxis: {{ title: 'Value (/rad)' }},
            height: 400
        }};

        Plotly.newPlot('dynamic-derivatives-plot', dynamicData, dynamicLayout, {{responsive: true}});

        // Elevon effectiveness
        const elevonData = [{{
            x: [-30, -20, -10, 0, 10, 20, 30],
            y: [-30, -20, -10, 0, 10, 20, 30].map(d => d * {Cm_de_per_deg}),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Cm',
            line: {{ color: '#667eea', width: 3 }}
        }}];

        const elevonLayout = {{
            title: 'Elevon Pitch Effectiveness',
            xaxis: {{ title: 'Elevon Deflection (deg)' }},
            yaxis: {{ title: 'Pitch Moment Coefficient' }},
            height: 400
        }};

        Plotly.newPlot('elevon-effectiveness-plot', elevonData, elevonLayout, {{responsive: true}});

        // Aileron effectiveness
        const aileronData = [{{
            x: [-30, -20, -10, 0, 10, 20, 30],
            y: [-30, -20, -10, 0, 10, 20, 30].map(d => d * {Cl_da_per_deg}),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Cl',
            line: {{ color: '#764ba2', width: 3 }}
        }}];

        const aileronLayout = {{
            title: 'Aileron Roll Effectiveness',
            xaxis: {{ title: 'Aileron Deflection (deg)' }},
            yaxis: {{ title: 'Roll Moment Coefficient' }},
            height: 400
        }};

        Plotly.newPlot('aileron-effectiveness-plot', aileronData, aileronLayout, {{responsive: true}});

        // Sample polars plot (simplified)
        const polarsData = [{{
            x: [-5, -4, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            y: [-0.39, -0.27, -0.05, 0.07, 0.18, 0.29, 0.40, 0.51, 0.62, 0.73, 0.84, 0.94, 1.05, 1.15, 1.25],
            type: 'scatter',
            mode: 'lines+markers',
            name: 'CL vs α',
            line: {{ color: '#667eea', width: 3 }}
        }}];

        const polarsLayout = {{
            title: 'Lift Coefficient vs Angle of Attack',
            xaxis: {{ title: 'Alpha (deg)' }},
            yaxis: {{ title: 'CL' }},
            height: 400
        }};

        Plotly.newPlot('polars-plot', polarsData, polarsLayout, {{responsive: true}});

        // Drag polar
        const dragPolarData = [{{
            x: [0.005, 0.006, 0.007, 0.008, 0.009, 0.010, 0.012, 0.015, 0.020, 0.030],
            y: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.5, 1.5],
            type: 'scatter',
            mode: 'lines+markers',
            name: 'CL vs CD',
            line: {{ color: '#764ba2', width: 3 }}
        }}];

        const dragPolarLayout = {{
            title: 'Drag Polar (CL vs CD)',
            xaxis: {{ title: 'CD' }},
            yaxis: {{ title: 'CL' }},
            height: 400
        }};

        Plotly.newPlot('drag-polar-plot', dragPolarData, dragPolarLayout, {{responsive: true}});
        """
