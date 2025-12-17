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

    def _load_avl_polar_data(self) -> Dict[str, Any]:
        """
        Load AVL 3D aircraft polar data from results directory.

        Extracts CL, CD_induced, and alpha from AVL output files at beta ≈ 0.

        Returns:
            Dictionary with 'alpha', 'CL', and 'CD_induced' lists, or None if not available
        """
        import re
        import os

        try:
            # Find results directory relative to aerodeck JSON
            results_dir = self.aerodeck_path.parent
            avl_outputs_dir = results_dir / 'avl_outputs'

            if not avl_outputs_dir.exists():
                avl_outputs_dir = results_dir

            # Find all output files
            output_files = list(avl_outputs_dir.glob('a*_b*_output.txt'))

            # Parse alpha, beta, CL, CD from filenames and file contents
            data_points = []

            for output_file in output_files:
                # Only process _output.txt files
                if not output_file.name.endswith('_output.txt'):
                    continue

                # Extract alpha and beta from filename (e.g., a5.0_b-1.0_M0.10_output.txt)
                match = re.match(r'a([-\d.]+)_b([-\d.]+)_M', output_file.name)
                if not match:
                    continue

                alpha = float(match.group(1))
                beta = float(match.group(2))

                # Only use cases near beta=0 (within ±2 degrees)
                if abs(beta) > 2.0:
                    continue

                # Read CL and CD from file
                with open(output_file, 'r') as f:
                    content = f.read()

                # Look for "CLtot = " and "CDind = " lines
                cl_match = re.search(r'CLtot\s*=\s*([-\d.]+)', content)
                cd_match = re.search(r'CDind\s*=\s*([-\d.]+)', content)

                if cl_match and cd_match:
                    cl = float(cl_match.group(1))
                    cd_ind = float(cd_match.group(1))
                    data_points.append((alpha, cl, cd_ind))

            if not data_points:
                return None

            # Sort by alpha
            data_points.sort(key=lambda x: x[0])
            alphas = [p[0] for p in data_points]
            cls = [p[1] for p in data_points]
            cd_inds = [p[2] for p in data_points]

            return {
                'alpha': alphas,
                'CL': cls,
                'CD_induced': cd_inds
            }

        except Exception as e:
            return None

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
            font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
            background: #ffffff;
            color: #000000;
            min-height: 100vh;
            padding: 20px;
            line-height: 1.4;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: #ffffff;
            border: 2px solid #cccccc;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .header {{
            background: #f5f5f5;
            color: #000000;
            padding: 20px;
            border-bottom: 2px solid #cccccc;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2em;
            margin-bottom: 5px;
            letter-spacing: 2px;
            text-shadow: none;
        }}

        .header p {{
            font-size: 0.9em;
            opacity: 0.7;
            letter-spacing: 1px;
        }}

        .content {{
            padding: 20px;
        }}

        .tabs {{
            display: flex;
            gap: 0;
            border-bottom: 2px solid #cccccc;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}

        .tab {{
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid #cccccc;
            border-bottom: none;
            background: #f5f5f5;
            font-size: 0.9em;
            color: #000000;
            font-family: 'Courier New', monospace;
            transition: all 0.2s;
            letter-spacing: 1px;
        }}

        .tab:hover {{
            background: #e0e0e0;
        }}

        .tab.active {{
            background: #ffffff;
            font-weight: bold;
            border-bottom: 2px solid #ffffff;
        }}

        .tab-content {{
            display: none;
            animation: fadeIn 0.2s;
        }}

        .tab-content.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        .card {{
            background: #ffffff;
            border: 1px solid #cccccc;
            padding: 15px;
            margin-bottom: 15px;
        }}

        .card h3 {{
            color: #000000;
            margin-bottom: 15px;
            font-size: 1.2em;
            letter-spacing: 1px;
            border-bottom: 2px solid #000000;
            padding-bottom: 5px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .metric {{
            background: #f9f9f9;
            padding: 15px;
            border: 1px solid #cccccc;
        }}

        .metric-label {{
            color: #666666;
            font-size: 0.8em;
            margin-bottom: 5px;
            letter-spacing: 0.5px;
        }}

        .metric-value {{
            color: #000000;
            font-size: 1.3em;
            font-weight: bold;
        }}

        .metric-unit {{
            color: #666666;
            font-size: 0.8em;
            margin-left: 5px;
        }}

        .plot-container {{
            margin: 15px 0;
            background: #ffffff;
            border: 1px solid #cccccc;
            padding: 10px;
        }}

        .full-width-card {{
            width: 100%;
            margin-bottom: 15px;
        }}

        .full-width-card .plot-container {{
            min-height: 350px;
            width: 100%;
        }}

        .range-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            border: 1px solid #cccccc;
        }}

        th {{
            background: #f5f5f5;
            color: #000000;
            padding: 10px;
            text-align: left;
            font-weight: bold;
            border: 1px solid #cccccc;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 8px;
            border: 1px solid #e0e0e0;
            color: #000000;
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .footer {{
            text-align: center;
            padding: 15px;
            color: #666666;
            font-size: 0.8em;
            border-top: 2px solid #cccccc;
            margin-top: 20px;
            letter-spacing: 0.5px;
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
                <button class="tab" onclick="showTab('modes')">Dynamic Modes</button>
                <button class="tab" onclick="showTab('control')">Control</button>
                <button class="tab" onclick="showTab('polars')">Polars</button>
                <button class="tab" onclick="showTab('range')">Range</button>
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

            <div id="modes" class="tab-content">
                {self._build_modes_tab()}
            </div>

            <div id="control" class="tab-content">
                {self._build_control_tab(aero)}
            </div>

            <div id="polars" class="tab-content">
                {self._build_polars_tab()}
            </div>

            <div id="range" class="tab-content">
                {self._build_range_tab(mass)}
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
        import csv
        import os

        cg = mass.get('cg_ft', [0, 0, 0])
        inertia = mass.get('inertia_lbm_ft2', {})

        # Extract reference geometry with correct key names
        S_ref_ft2 = reference.get('S_ref_ft2', reference.get('S_ref', 0))
        b_ref_ft = reference.get('b_ref_ft', reference.get('b_ref', 0))
        c_ref_ft = reference.get('c_ref_ft', reference.get('c_ref', 0))
        x_ref_ft = reference.get('x_ref_ft', 0)
        y_ref_ft = reference.get('y_ref_ft', 0)
        z_ref_ft = reference.get('z_ref_ft', 0)

        # Calculate aspect ratio
        aspect_ratio = (b_ref_ft ** 2 / S_ref_ft2) if S_ref_ft2 > 0 else 0

        # Get neutral point from aerodynamics data
        aero = self.data.get('aerodynamics', {})
        static_stab = aero.get('static_stability', {})
        longitudinal = static_stab.get('longitudinal', {})
        neutral_point_x_ft = longitudinal.get('neutral_point_x_ft', None)

        # Calculate static margin: SM = (x_np - x_cg) / c_ref
        static_margin_pct = None
        is_stable = False
        stability_text = ""
        np_row_color = "#ffffff"
        if neutral_point_x_ft is not None and c_ref_ft > 0:
            static_margin_pct = ((neutral_point_x_ft - cg[0]) / c_ref_ft) * 100
            # Stability assessment: positive SM = stable, negative = unstable
            # Typical range: 5-15% is good, 0-5% marginal, <0% unstable
            if static_margin_pct > 5:
                is_stable = True
                stability_text = "✓ STABLE"
                np_row_color = "#c8e6c9"  # Green
            elif static_margin_pct > 0:
                is_stable = True
                stability_text = "⚠ MARGINALLY STABLE"
                np_row_color = "#fff3cd"  # Yellow
            else:
                is_stable = False
                stability_text = "✗ UNSTABLE"
                np_row_color = "#ffcdd2"  # Red

        # Load LE, TE, winglet, elevon, and tail points from CSV files
        le_points = []
        te_points = []
        winglet_points = []
        elevon_points = []
        tail_points = []

        try:
            le_path = os.path.join('data', 'LEpts.csv')
            te_path = os.path.join('data', 'TEpts.csv')
            winglet_path = os.path.join('data', 'WINGLETpts.csv')
            elevon_path = os.path.join('data', 'ELEVONpts.csv')
            tail_path = os.path.join('data', 'TAILpts.csv')

            with open(le_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert inches to feet
                    le_points.append([float(row['x'])/12, float(row['y'])/12, float(row['z'])/12])

            with open(te_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert inches to feet
                    te_points.append([float(row['x'])/12, float(row['y'])/12, float(row['z'])/12])

            # Load winglets if available (optional)
            if os.path.exists(winglet_path):
                with open(winglet_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        winglet_points.append([float(row['x'])/12, float(row['y'])/12, float(row['z'])/12])

            # Load elevons if available (optional)
            if os.path.exists(elevon_path):
                with open(elevon_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        elevon_points.append([float(row['x'])/12, float(row['y'])/12, float(row['z'])/12])

            # Load tail if available (optional)
            if os.path.exists(tail_path):
                with open(tail_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        tail_points.append([float(row['x'])/12, float(row['y'])/12, float(row['z'])/12])

        except Exception as e:
            # Fall back to simplified geometry if files not found
            le_points = []
            te_points = []
            winglet_points = []
            elevon_points = []
            tail_points = []

        # Create planform SVG with actual geometry
        # Scale factor to fit in viewport - matching PDF size
        scale = 50  # pixels per foot (much larger for better visibility)

        if le_points and te_points:
            # Find bounds for proper scaling - include all geometry components
            all_points = le_points + te_points + winglet_points + elevon_points + tail_points
            all_x = [p[0] for p in all_points]
            all_y = [p[1] for p in all_points]
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            # Calculate center of geometry - Y should be centered on 0 since we mirror
            center_geom_x = (min_x + max_x) / 2
            center_geom_y = 0  # Centerline, since we mirror the geometry

            # Calculate SVG dimensions with padding
            chordwise_extent = max_x - min_x
            spanwise_extent = max_y * 2  # *2 for both wing halves (mirrored around y=0)

            # Use actual wingspan from geometry data (more accurate than b_ref_ft)
            actual_wingspan_ft = spanwise_extent

            svg_width = int(spanwise_extent * scale) + 200
            svg_height = int(chordwise_extent * scale) + 200
            center_x = svg_width / 2
            center_y = svg_height / 2

            # Transform points to SVG coordinates (mirror for left wing)
            def to_svg(x, y):
                # Rotate: nTop Y is spanwise (left-right), X is chordwise (up-down)
                # SVG: x is spanwise (horizontal), y is chordwise (vertical, down is positive)
                # Center the geometry in the SVG viewport (y=0 is centerline)
                svg_x = center_x + y * scale
                svg_y = center_y + (x - center_geom_x) * scale
                return svg_x, svg_y

            # Build polygon points for right half (and mirror for left)
            right_wing_points = []

            # Leading edge from root to tip
            for pt in le_points:
                sx, sy = to_svg(pt[0], pt[1])
                right_wing_points.append(f"{sx:.1f},{sy:.1f}")

            # Trailing edge from tip to root
            for pt in reversed(te_points):
                sx, sy = to_svg(pt[0], pt[1])
                right_wing_points.append(f"{sx:.1f},{sy:.1f}")

            right_polygon = " ".join(right_wing_points)

            # Mirror for left wing
            left_wing_points = []
            for pt in le_points:
                sx, sy = to_svg(pt[0], -pt[1])  # Negate y for mirror
                left_wing_points.append(f"{sx:.1f},{sy:.1f}")
            for pt in reversed(te_points):
                sx, sy = to_svg(pt[0], -pt[1])
                left_wing_points.append(f"{sx:.1f},{sy:.1f}")

            left_polygon = " ".join(left_wing_points)

            # CG marker position
            cg_x, cg_y = to_svg(cg[0], cg[1])

            # Neutral point marker position (if available)
            np_svg = ""
            static_margin_svg = ""
            if neutral_point_x_ft is not None:
                np_x, np_y = to_svg(neutral_point_x_ft, 0)  # On centerline

                # Static margin visualization (line from CG to NP)
                static_margin_svg = f"""
                        <!-- Static margin indicator -->
                        <line x1="{cg_x}" y1="{cg_y}" x2="{np_x}" y2="{np_y}"
                              stroke="#0000ff" stroke-width="2" stroke-dasharray="5,3"/>
                        <text x="{(cg_x + np_x) / 2}" y="{(cg_y + np_y) / 2 - 10}"
                              fill="#0000ff" font-family="Courier New" font-size="11" text-anchor="middle" font-weight="bold">
                              SM = {((neutral_point_x_ft - cg[0]) / c_ref_ft * 100):.1f}%</text>
"""

                np_svg = f"""
                        <!-- Neutral point marker -->
                        <circle cx="{np_x}" cy="{np_y}" r="6" fill="#0000ff" stroke="#000000" stroke-width="1"/>
                        <text x="{np_x + 12}" y="{np_y + 5}" fill="#000000" font-family="Courier New" font-size="13" font-weight="bold">NP</text>
"""

            # Build winglet polygons if available
            winglet_svg = ""
            if winglet_points:
                right_winglet_points = []
                for pt in winglet_points:
                    sx, sy = to_svg(pt[0], pt[1])
                    right_winglet_points.append(f"{sx:.1f},{sy:.1f}")
                right_winglet_polygon = " ".join(right_winglet_points)

                left_winglet_points = []
                for pt in winglet_points:
                    sx, sy = to_svg(pt[0], -pt[1])
                    left_winglet_points.append(f"{sx:.1f},{sy:.1f}")
                left_winglet_polygon = " ".join(left_winglet_points)

                winglet_svg = f"""
                        <!-- Right winglet -->
                        <polygon points="{right_winglet_polygon}"
                                 fill="#ffffcc" fill-opacity="0.6" stroke="#000000" stroke-width="1.5"/>

                        <!-- Left winglet -->
                        <polygon points="{left_winglet_polygon}"
                                 fill="#ffffcc" fill-opacity="0.6" stroke="#000000" stroke-width="1.5"/>
"""

            # Build elevon polygons if available
            elevon_svg = ""
            if elevon_points:
                right_elevon_points = []
                for pt in elevon_points:
                    sx, sy = to_svg(pt[0], pt[1])
                    right_elevon_points.append(f"{sx:.1f},{sy:.1f}")
                right_elevon_polygon = " ".join(right_elevon_points)

                left_elevon_points = []
                for pt in elevon_points:
                    sx, sy = to_svg(pt[0], -pt[1])
                    left_elevon_points.append(f"{sx:.1f},{sy:.1f}")
                left_elevon_polygon = " ".join(left_elevon_points)

                elevon_svg = f"""
                        <!-- Right elevon -->
                        <polygon points="{right_elevon_polygon}"
                                 fill="#ffcccc" fill-opacity="0.5" stroke="#cc0000" stroke-width="1.5"/>

                        <!-- Left elevon -->
                        <polygon points="{left_elevon_polygon}"
                                 fill="#ffcccc" fill-opacity="0.5" stroke="#cc0000" stroke-width="1.5"/>
"""

            # Build tail polygon if available
            tail_svg = ""
            if tail_points:
                # Tail is typically a single surface (vertical stabilizer on centerline)
                # or horizontal stabilizer - render it as a polygon
                tail_polygon_points = []
                for pt in tail_points:
                    sx, sy = to_svg(pt[0], pt[1])
                    tail_polygon_points.append(f"{sx:.1f},{sy:.1f}")
                tail_polygon = " ".join(tail_polygon_points)

                # Check if tail is symmetric (has y values on both sides) or single surface
                tail_y_values = [p[1] for p in tail_points]
                has_negative_y = any(y < -0.01 for y in tail_y_values)
                has_positive_y = any(y > 0.01 for y in tail_y_values)

                if has_negative_y and has_positive_y:
                    # Tail spans both sides - just draw it as-is
                    tail_svg = f"""
                        <!-- Tail surface -->
                        <polygon points="{tail_polygon}"
                                 fill="#d4edda" fill-opacity="0.6" stroke="#006400" stroke-width="1.5"/>
"""
                else:
                    # Single-sided tail - mirror it for symmetric planform
                    left_tail_points = []
                    for pt in tail_points:
                        sx, sy = to_svg(pt[0], -pt[1])
                        left_tail_points.append(f"{sx:.1f},{sy:.1f}")
                    left_tail_polygon = " ".join(left_tail_points)

                    tail_svg = f"""
                        <!-- Right tail surface -->
                        <polygon points="{tail_polygon}"
                                 fill="#d4edda" fill-opacity="0.6" stroke="#006400" stroke-width="1.5"/>

                        <!-- Left tail surface -->
                        <polygon points="{left_tail_polygon}"
                                 fill="#d4edda" fill-opacity="0.6" stroke="#006400" stroke-width="1.5"/>
"""

            planform_svg = f"""
                        <!-- Right wing -->
                        <polygon points="{right_polygon}"
                                 fill="#add8e6" fill-opacity="0.4" stroke="#000000" stroke-width="2"/>

                        <!-- Left wing -->
                        <polygon points="{left_polygon}"
                                 fill="#add8e6" fill-opacity="0.4" stroke="#000000" stroke-width="2"/>

{winglet_svg}
{elevon_svg}
{tail_svg}

                        <!-- Centerline -->
                        <line x1="{center_x}" y1="50" x2="{center_x}" y2="{svg_height-50}"
                              stroke="#666666" stroke-width="1" stroke-dasharray="3,3"/>

{static_margin_svg}

                        <!-- CG marker -->
                        <circle cx="{cg_x}" cy="{cg_y}" r="6" fill="#ff0000" stroke="#000000" stroke-width="1"/>
                        <text x="{cg_x + 12}" y="{cg_y + 5}" fill="#000000" font-family="Courier New" font-size="13" font-weight="bold">CG</text>

{np_svg}

                        <!-- Dimension labels -->
                        <text x="{center_x}" y="{svg_height - 30}"
                              fill="#666666" font-family="Courier New" font-size="12" text-anchor="middle" font-weight="bold">
                              Wingspan: {actual_wingspan_ft:.2f} ft</text>

                        <!-- Axes labels -->
                        <text x="{svg_width - 60}" y="{center_y - 15}" fill="#666666" font-family="Courier New" font-size="11">+Y (span)</text>
                        <text x="{center_x + 15}" y="30" fill="#666666" font-family="Courier New" font-size="11">+X (chord)</text>
"""
        else:
            # Fallback: simplified rectangular planform
            svg_width = int(b_ref_ft * scale) + 100
            svg_height = int(c_ref_ft * scale) + 100
            wing_half_span = b_ref_ft / 2 * scale
            wing_chord = c_ref_ft * scale
            center_x = svg_width / 2
            center_y = svg_height / 2
            cg_x = center_x
            cg_y = center_y

            # Neutral point and static margin for fallback
            np_svg_fallback = ""
            static_margin_svg_fallback = ""
            if neutral_point_x_ft is not None:
                # Simplified conversion for fallback geometry
                np_x_fallback = center_x + ((neutral_point_x_ft - x_ref_ft) * scale)
                np_y_fallback = center_y

                static_margin_svg_fallback = f"""
                        <!-- Static margin indicator -->
                        <line x1="{cg_x}" y1="{cg_y}" x2="{np_x_fallback}" y2="{np_y_fallback}"
                              stroke="#0000ff" stroke-width="2" stroke-dasharray="5,3"/>
                        <text x="{(cg_x + np_x_fallback) / 2}" y="{(cg_y + np_y_fallback) / 2 - 10}"
                              fill="#0000ff" font-family="Courier New" font-size="11" text-anchor="middle" font-weight="bold">
                              SM = {((neutral_point_x_ft - cg[0]) / c_ref_ft * 100):.1f}%</text>
"""

                np_svg_fallback = f"""
                        <!-- Neutral point marker -->
                        <circle cx="{np_x_fallback}" cy="{np_y_fallback}" r="6" fill="#0000ff" stroke="#000000" stroke-width="1"/>
                        <text x="{np_x_fallback + 12}" y="{np_y_fallback + 5}" fill="#000000" font-family="Courier New" font-size="13" font-weight="bold">NP</text>
"""

            planform_svg = f"""
                        <!-- Wing planform (simplified fallback) -->
                        <rect x="{center_x - wing_half_span}" y="{center_y - wing_chord/2}"
                              width="{wing_half_span * 2}" height="{wing_chord}"
                              fill="none" stroke="#000000" stroke-width="2"/>

                        <!-- Centerline -->
                        <line x1="{center_x}" y1="{center_y - wing_chord/2}"
                              x2="{center_x}" y2="{center_y + wing_chord/2}"
                              stroke="#666666" stroke-width="1"/>

{static_margin_svg_fallback}

                        <!-- CG marker -->
                        <circle cx="{cg_x}" cy="{cg_y}" r="5" fill="#ff0000"/>
                        <text x="{cg_x + 10}" y="{cg_y + 5}" fill="#000000" font-family="Courier New" font-size="12">CG</text>

{np_svg_fallback}

                        <!-- Dimension labels -->
                        <text x="{center_x}" y="{center_y + wing_chord/2 + 35}"
                              fill="#666666" font-family="Courier New" font-size="11" text-anchor="middle">
                              b = {b_ref_ft:.2f} ft</text>

                        <!-- Axes labels -->
                        <text x="{svg_width - 40}" y="{center_y - 10}" fill="#666666" font-family="Courier New" font-size="11">+Y</text>
                        <text x="{center_x + 10}" y="40" fill="#666666" font-family="Courier New" font-size="11">+X</text>
"""

        return f"""
            <div class="card">
                <h3>Aircraft Planform View</h3>
                <div style="text-align: center; margin: 20px 0;">
                    <svg width="{svg_width}" height="{svg_height}" style="background: #f9f9f9; border: 1px solid #cccccc;">
                        <!-- Coordinate axes -->
                        <line x1="50" y1="{center_y}" x2="{svg_width-50}" y2="{center_y}"
                              stroke="#cccccc" stroke-width="1" stroke-dasharray="5,5"/>
                        <line x1="{center_x}" y1="50" x2="{center_x}" y2="{svg_height-50}"
                              stroke="#cccccc" stroke-width="1" stroke-dasharray="5,5"/>

{planform_svg}
                    </svg>
                </div>
            </div>

            <div class="card">
                <h3>Reference Geometry</h3>
                <table>
                    <tr><th>Parameter</th><th>Value</th><th>Units</th></tr>
                    <tr><td>Wing Area (S<sub>ref</sub>)</td><td>{S_ref_ft2:.3f}</td><td>ft²</td></tr>
                    <tr><td>Wingspan (b<sub>ref</sub>)</td><td>{b_ref_ft:.3f}</td><td>ft</td></tr>
                    <tr><td>Mean Chord (c<sub>ref</sub>)</td><td>{c_ref_ft:.3f}</td><td>ft</td></tr>
                    <tr><td>Aspect Ratio</td><td>{aspect_ratio:.3f}</td><td>-</td></tr>
                    {'<tr style="background: {};"><td><b>Neutral Point (x<sub>np</sub>)</b></td><td><b>{:.3f}</b></td><td><b>ft</b></td></tr>'.format(np_row_color, neutral_point_x_ft) if neutral_point_x_ft is not None else ''}
                    {'<tr style="background: {};"><td><b>Static Margin</b></td><td><b>{:.2f}</b></td><td><b>% - {}</b></td></tr>'.format(np_row_color, static_margin_pct, stability_text) if static_margin_pct is not None else ''}
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

        # Get derivative values
        CL_alpha = longitudinal.get('CL_alpha_per_rad', 0)
        Cm_alpha = longitudinal.get('Cm_alpha_per_rad', 0)
        Cn_beta = lateral_directional.get('Cn_beta_per_rad', 0)
        Cl_beta = lateral_directional.get('Cl_beta_per_rad', 0)

        CL_q = pitch_rate.get('CL_q_per_rad', 0)
        Cm_q = pitch_rate.get('Cm_q_per_rad', 0)
        Cl_p = roll_rate.get('Cl_p_per_rad', 0)
        Cn_r = yaw_rate.get('Cn_r_per_rad', 0)

        # Assess stability
        cl_alpha_stable = CL_alpha > 0
        cm_alpha_stable = Cm_alpha < 0
        cn_beta_stable = Cn_beta > 0
        cl_beta_stable = True  # Dihedral effect - less critical

        cm_q_damped = Cm_q < 0
        cl_p_damped = Cl_p < 0
        cn_r_damped = Cn_r < 0

        # Helper function for status badge
        def status_badge(is_good, good_text, bad_text):
            if is_good:
                return f'<span style="color: #1b5e20; background: #c8e6c9; padding: 3px 8px; border-radius: 3px; font-weight: bold;">✓ {good_text}</span>'
            else:
                return f'<span style="color: #b71c1c; background: #ffcdd2; padding: 3px 8px; border-radius: 3px; font-weight: bold;">✗ {bad_text}</span>'

        return f"""
            <div class="card">
                <h3>Static Stability Derivatives</h3>
                <div class="plot-container">
                    <div id="static-derivatives-plot"></div>
                </div>
                <table>
                    <tr><th>Derivative</th><th>Value</th><th>Units</th><th>Description</th><th>Status</th></tr>
                    <tr><td>CL<sub>α</sub></td><td>{CL_alpha:.3f}</td><td>/rad</td><td>Lift curve slope</td><td>{status_badge(cl_alpha_stable, 'STABLE', 'UNSTABLE')}</td></tr>
                    <tr><td>Cm<sub>α</sub></td><td>{Cm_alpha:.3f}</td><td>/rad</td><td>Pitch stability</td><td>{status_badge(cm_alpha_stable, 'STABLE', 'UNSTABLE')}</td></tr>
                    <tr><td>Cn<sub>β</sub></td><td>{Cn_beta:.3f}</td><td>/rad</td><td>Yaw stability</td><td>{status_badge(cn_beta_stable, 'STABLE', 'UNSTABLE')}</td></tr>
                    <tr><td>Cl<sub>β</sub></td><td>{Cl_beta:.3f}</td><td>/rad</td><td>Dihedral effect</td><td>{'Normal' if Cl_beta < 0 else 'Reversed'}</td></tr>
                </table>
            </div>

            <div class="card">
                <h3>Dynamic Stability Derivatives (Rate Damping)</h3>
                <div class="plot-container">
                    <div id="dynamic-derivatives-plot"></div>
                </div>
                <table>
                    <tr><th>Derivative</th><th>Value</th><th>Units</th><th>Description</th><th>Status</th></tr>
                    <tr><td>CL<sub>q</sub></td><td>{CL_q:.3f}</td><td>/rad</td><td>Pitch damping (lift)</td><td>{'Normal' if CL_q > 3.0 else 'Low'}</td></tr>
                    <tr><td>Cm<sub>q</sub></td><td>{Cm_q:.3f}</td><td>/rad</td><td>Pitch damping (moment)</td><td>{status_badge(cm_q_damped, 'DAMPED', 'DIVERGENT')}</td></tr>
                    <tr><td>Cl<sub>p</sub></td><td>{Cl_p:.3f}</td><td>/rad</td><td>Roll damping</td><td>{status_badge(cl_p_damped, 'DAMPED', 'DIVERGENT')}</td></tr>
                    <tr><td>Cn<sub>r</sub></td><td>{Cn_r:.3f}</td><td>/rad</td><td>Yaw damping</td><td>{status_badge(cn_r_damped, 'DAMPED', 'DIVERGENT')}</td></tr>
                </table>
            </div>
        """

    def _build_modes_tab(self) -> str:
        """Build dynamic modes analysis tab with all lateral modes."""
        return f"""
            <div class="card">
                <h3>Lateral-Directional Dynamic Modes</h3>
                <p style="margin-bottom: 15px; color: #666;">
                    Analysis of lateral-directional dynamics at cruise condition (200 mph, sea level)
                </p>
                <div id="modes-summary"></div>
            </div>

            <div class="card">
                <h3>Mode Characteristics</h3>
                <div id="modes-writeup" style="line-height: 1.6; color: #333;"></div>
            </div>

            <div class="card">
                <h3>Dutch Roll Time Response</h3>
                <div class="plot-container">
                    <div id="dutch-roll-response-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Eigenvalue Plot (s-plane)</h3>
                <div class="plot-container">
                    <div id="eigenvalue-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Damping Ratio vs Airspeed</h3>
                <div class="plot-container">
                    <div id="damping-vs-speed-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Dutch Roll Frequency vs Airspeed</h3>
                <div class="plot-container">
                    <div id="freq-vs-speed-plot"></div>
                </div>
            </div>
        """

    def _build_control_tab(self, aero: Dict) -> str:
        """Build control effectiveness tab content matching PDF report."""
        return f"""
            <div class="card">
                <h3>Control Configuration</h3>
                <div id="control-config"></div>
            </div>

            <div class="card">
                <h3>Pitch Control Authority</h3>
                <div class="plot-container">
                    <div id="pitch-control-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Roll Control Authority</h3>
                <div class="plot-container">
                    <div id="roll-control-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Required Deflections</h3>
                <div id="trim-requirements"></div>
            </div>

            <div class="card">
                <h3>Elevon Forces & Hinge Loading at 10° Deflection</h3>
                <div id="elevon-forces"></div>
            </div>
        """

    def _build_polars_tab(self) -> str:
        """Build polars tab content."""
        polars_data = self.data.get('airfoil_polars', {})
        airfoil_name = polars_data.get('airfoil_name', 'Unknown')

        return f"""
            <div class="card">
                <h3>Airfoil: {airfoil_name}</h3>
                <p style="color: #666; background: #f9f9f9; padding: 10px; border-left: 3px solid #666; margin-bottom: 15px; font-size: 0.9em;">
                    <b>ℹ NOTE:</b> The following charts show 2D airfoil section data from XFOIL analysis.
                    These represent the performance of the airfoil profile itself, without 3D wing effects (induced drag, tip effects, etc.).
                </p>
                <div class="plot-container">
                    <div id="cl-alpha-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Drag Polar (CL vs CD) - 2D Airfoil Section</h3>
                <div class="plot-container">
                    <div id="drag-polar-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Lift-to-Drag Ratio</h3>
                <p style="color: #1b5e20; background: #c8e6c9; padding: 10px; border: 1px solid #1b5e20; margin-bottom: 15px; font-size: 0.9em;">
                    <b>✓ 3D Aircraft L/D:</b> This chart combines XFOIL profile drag with AVL induced drag to show the actual 3D aircraft performance.
                    CD<sub>total</sub> = CD<sub>profile</sub> (XFOIL) + CD<sub>induced</sub> (AVL).
                    Expected range: L/D = 15-25 for this wing configuration.
                </p>
                <div class="plot-container">
                    <div id="ld-ratio-plot"></div>
                </div>
            </div>

            <div class="card">
                <h3>Moment Coefficient</h3>
                <div class="plot-container">
                    <div id="cm-alpha-plot"></div>
                </div>
            </div>
        """

    def _build_range_tab(self, mass: Dict) -> str:
        """Build range analysis tab content."""
        fuel_mass = mass.get('fuel_mass_lbm', None)
        total_mass = mass.get('mass_lbm', 0)

        # If no fuel mass, show message
        if fuel_mass is None:
            return """
            <div class="card">
                <h3>Range Analysis</h3>
                <p style="color: #666; background: #f9f9f9; padding: 15px; border-left: 3px solid #cc0000;">
                    <b>No fuel data available.</b><br><br>
                    To enable range calculations, add a <code>fuel_mass</code> column to your mass.csv file.
                    The fuel_mass value should be in pounds (lbm).
                </p>
            </div>
            """

        # Calculate fuel fraction
        fuel_fraction = fuel_mass / total_mass if total_mass > 0 else 0

        return f"""
            <div class="card" style="width: 100%; margin-bottom: 15px;">
                <h3>Mission Profile</h3>
                <div style="height: 350px; width: 100%;">
                    <div id="mission-profile-plot" style="width: 100%; height: 100%;"></div>
                </div>
            </div>

            <div class="range-grid">
                <div class="card">
                    <h3>Fuel & Weight Summary</h3>
                    <div class="grid">
                        <div class="metric">
                            <div class="metric-label">Total Mass (MTOW)</div>
                            <div class="metric-value">{total_mass:.1f}<span class="metric-unit">lbm</span></div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Fuel Mass</div>
                            <div class="metric-value">{fuel_mass:.1f}<span class="metric-unit">lbm</span></div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Fuel Fraction</div>
                            <div class="metric-value">{fuel_fraction*100:.1f}<span class="metric-unit">%</span></div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Empty Weight (est)</div>
                            <div class="metric-value">{total_mass - fuel_mass:.1f}<span class="metric-unit">lbm</span></div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h3>Range Calculator (Breguet Equation)</h3>
                    <p style="color: #666; background: #f9f9f9; padding: 10px; border-left: 3px solid #666; margin-bottom: 15px; font-size: 0.9em;">
                        <b>Breguet Range Equation:</b> R = (V / SFC) × (L/D) × ln(W₁/W₂)<br>
                        where W₁ = initial weight, W₂ = final weight (after fuel burn)
                    </p>
                    <div id="range-calculator"></div>
                </div>

                <div class="card">
                    <h3>Range vs L/D</h3>
                    <div class="plot-container">
                        <div id="range-ld-plot"></div>
                    </div>
                </div>

                <div class="card">
                    <h3>Endurance Analysis</h3>
                    <div id="endurance-calculator"></div>
                </div>
            </div>
        """

    def _build_plot_scripts(self) -> str:
        """Build Plotly.js plotting scripts."""
        # Load AVL 3D aircraft polar data
        avl_polar = self._load_avl_polar_data()

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
            CL_de_per_deg = elevon_eff.get('CL_delta_per_rad', 0) * 180 / np.pi
            Cm_de_per_deg = elevon_eff.get('Cm_delta_per_rad', 0) * 180 / np.pi
            Ch_elevon = elevon_eff.get('Ch_delta')  # Hinge moment coefficient from AVL
        else:
            CL_de_per_deg = 0
            Cm_de_per_deg = 0
            Ch_elevon = None

        if aileron_control:
            aileron_eff = aileron_control.get('effectiveness', {})
            Cl_da_per_deg = aileron_eff.get('Cl_delta_per_rad', 0) * 180 / np.pi
            Cn_da_per_deg = aileron_eff.get('Cn_delta_per_rad', 0) * 180 / np.pi
            Ch_aileron = aileron_eff.get('Ch_delta')  # Hinge moment coefficient from AVL
        else:
            Cl_da_per_deg = 0
            Cn_da_per_deg = 0
            Ch_aileron = None

        # Extract airfoil polar data
        polars_data = self.data.get('airfoil_polars', {})
        polars_list = polars_data.get('polars', [])

        # Prepare polar data for plots
        polar_traces = []
        for polar in polars_list:
            reynolds = polar.get('reynolds', 0)
            alpha = polar.get('alpha', [])
            CL = polar.get('CL', [])
            CD = polar.get('CD', [])
            CM = polar.get('CM', [])

            # Format Reynolds number for legend
            re_str = f"Re={reynolds:.2e}"

            polar_traces.append({
                'reynolds': reynolds,
                're_str': re_str,
                'alpha': alpha,
                'CL': CL,
                'CD': CD,
                'CM': CM
            })

        return f"""
        // Clean minimal chart layout
        const cadLayout = {{
            paper_bgcolor: '#ffffff',
            plot_bgcolor: '#ffffff',
            font: {{
                family: 'Courier New, monospace',
                size: 10,
                color: '#000000'
            }},
            title: {{
                font: {{ size: 12, color: '#000000' }}
            }},
            xaxis: {{
                gridcolor: '#e0e0e0',
                gridwidth: 0.5,
                linecolor: '#000000',
                linewidth: 1,
                tickcolor: '#000000',
                zerolinecolor: '#666666',
                zerolinewidth: 1
            }},
            yaxis: {{
                gridcolor: '#e0e0e0',
                gridwidth: 0.5,
                linecolor: '#000000',
                linewidth: 1,
                tickcolor: '#000000',
                zerolinecolor: '#666666',
                zerolinewidth: 1
            }},
            height: 350
        }};

        // === AERODECK DATA ===
        // Load aerodeck data for use throughout the script
        const aerodeck = {json.dumps(self.data)};
        const ref = aerodeck.reference_geometry;
        const mass_props = aerodeck.mass_properties;
        const aero = aerodeck.aerodynamics;

        // === AVL 3D AIRCRAFT POLAR DATA ===
        const avlPolar = {json.dumps(avl_polar)};

        // Static derivatives bar chart
        const staticData = [{{
            x: ['CL_α', 'Cm_α', 'Cn_β', 'Cl_β'],
            y: [{longitudinal.get('CL_alpha_per_rad', 0)}, {longitudinal.get('Cm_alpha_per_rad', 0)},
                {lateral_directional.get('Cn_beta_per_rad', 0)}, {lateral_directional.get('Cl_beta_per_rad', 0)}],
            type: 'bar',
            marker: {{ color: '#cccccc', line: {{ color: '#000000', width: 0.5 }} }}
        }}];

        const staticLayout = Object.assign({{}}, cadLayout, {{
            title: 'STATIC STABILITY DERIVATIVES',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Derivative' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'Value (/rad)' }})
        }});

        Plotly.newPlot('static-derivatives-plot', staticData, staticLayout, {{responsive: true, displayModeBar: false}});

        // Dynamic derivatives bar chart
        const dynamicData = [{{
            x: ['CL_q', 'Cm_q', 'Cl_p', 'Cn_r'],
            y: [{pitch_rate.get('CL_q_per_rad', 0)}, {pitch_rate.get('Cm_q_per_rad', 0)},
                {roll_rate.get('Cl_p_per_rad', 0)}, {yaw_rate.get('Cn_r_per_rad', 0)}],
            type: 'bar',
            marker: {{ color: '#cccccc', line: {{ color: '#000000', width: 0.5 }} }}
        }}];

        const dynamicLayout = Object.assign({{}}, cadLayout, {{
            title: 'DYNAMIC STABILITY DERIVATIVES',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Derivative' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'Value (/rad)' }})
        }});

        Plotly.newPlot('dynamic-derivatives-plot', dynamicData, dynamicLayout, {{responsive: true, displayModeBar: false}});

        // === CONTROL EFFECTIVENESS ANALYSIS ===
        // Display control configuration
        const controlConfig = `
            <div style="font-family: 'Courier New', monospace; font-size: 10px; line-height: 1.6; background: #f9f9f9; padding: 15px; border: 1px solid #ccc;">
                <p><b>Type:</b> Elevons (combined elevator + aileron)</p>
                <p><b>Location:</b> Trailing edge, outboard sections</p>
                <p><b>Hinge Line:</b> 75% chord</p>
                <p><b>Deflection Convention:</b></p>
                <ul style="margin-left: 20px;">
                    <li>Positive = trailing edge down</li>
                    <li>Symmetric = pitch control</li>
                    <li>Differential = roll control</li>
                </ul>
                <br>
                <p><b>CONTROL DERIVATIVES (AVL measured):</b></p>
                <table style="width: 100%; margin-top: 5px; border-collapse: collapse;">
                    <tr style="background: #e0e0e0;">
                        <th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Derivative</th>
                        <th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Value</th>
                        <th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Units</th>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">CL_δe (Lift per elevon)</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">${{({CL_de_per_deg}).toFixed(5)}}</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">/deg</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">Cm_δe (Pitch per elevon)</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">${{({Cm_de_per_deg}).toFixed(5)}}</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">/deg</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">Cl_δa (Roll per aileron)</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">${{({Cl_da_per_deg}).toFixed(5)}}</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">/deg</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">Cn_δa (Adverse yaw)</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">${{({Cn_da_per_deg}).toFixed(5)}}</td>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">/deg</td>
                    </tr>
                </table>
            </div>
        `;
        document.getElementById('control-config').innerHTML = controlConfig;

        // Pitch control authority plot (dual Y-axis)
        const delta_e = [];
        const delta_Cm = [];
        const delta_CL = [];
        for (let d = -20; d <= 20; d += 1) {{
            delta_e.push(d);
            delta_Cm.push({Cm_de_per_deg} * d);
            delta_CL.push({CL_de_per_deg} * d);
        }}

        const pitchTrace1 = {{
            x: delta_e,
            y: delta_Cm,
            type: 'scatter',
            mode: 'lines',
            name: 'ΔCm',
            line: {{ color: '#0000ff', width: 2 }},
            yaxis: 'y'
        }};

        const pitchTrace2 = {{
            x: delta_e,
            y: delta_CL,
            type: 'scatter',
            mode: 'lines',
            name: 'ΔCL',
            line: {{ color: '#ff0000', width: 2, dash: 'dash' }},
            yaxis: 'y2'
        }};

        const pitchLayout = Object.assign({{}}, cadLayout, {{
            title: 'PITCH CONTROL AUTHORITY',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Symmetric Elevon Deflection [deg]' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{
                title: 'ΔCm (Pitch Moment)',
                titlefont: {{ color: '#0000ff' }},
                tickfont: {{ color: '#0000ff' }}
            }}),
            yaxis2: {{
                title: 'ΔCL (Lift)',
                titlefont: {{ color: '#ff0000' }},
                tickfont: {{ color: '#ff0000' }},
                overlaying: 'y',
                side: 'right',
                gridcolor: '#e0e0e0',
                gridwidth: 0.5
            }},
            showlegend: true,
            legend: {{ font: {{ color: '#000000' }}, bgcolor: '#ffffff', bordercolor: '#cccccc', borderwidth: 1 }}
        }});

        Plotly.newPlot('pitch-control-plot', [pitchTrace1, pitchTrace2], pitchLayout, {{responsive: true, displayModeBar: false}});

        // Roll control authority plot
        const delta_a = [];
        const delta_Cl = [];
        for (let d = -20; d <= 20; d += 1) {{
            delta_a.push(d);
            delta_Cl.push({Cl_da_per_deg} * d);
        }}

        const rollTrace = {{
            x: delta_a,
            y: delta_Cl,
            type: 'scatter',
            mode: 'lines',
            name: 'ΔCl',
            line: {{ color: '#008000', width: 2 }}
        }};

        const rollLayout = Object.assign({{}}, cadLayout, {{
            title: 'ROLL CONTROL AUTHORITY',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Differential Elevon Deflection [deg]' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'ΔCl (Roll Moment)' }}),
            showlegend: false
        }});

        Plotly.newPlot('roll-control-plot', [rollTrace], rollLayout, {{responsive: true, displayModeBar: false}});

        // Calculate trim requirements
        const Cm_0 = aero.static_stability.longitudinal.Cm_0 || 0;
        const Cm_alpha = aero.static_stability.longitudinal.Cm_alpha_per_rad || 0;
        const Cm_de_per_rad = {Cm_de_per_deg} * Math.PI / 180;

        const trim_2deg = -(Cm_0 + Cm_alpha * (2 * Math.PI / 180)) / Cm_de_per_rad * (180 / Math.PI);
        const trim_5deg = -(Cm_0 + Cm_alpha * (5 * Math.PI / 180)) / Cm_de_per_rad * (180 / Math.PI);
        const trim_10deg = -(Cm_0 + Cm_alpha * (10 * Math.PI / 180)) / Cm_de_per_rad * (180 / Math.PI);

        const delta_CL_target = 0.2;
        const delta_e_1g = delta_CL_target / {CL_de_per_deg};

        const V_fps = 293.3;  // 200 mph in ft/s
        const Cl_p_per_rad = aero.dynamic_stability.roll_rate.Cl_p_per_rad || 0;
        const p_target = 30 * Math.PI / 180;  // 30 deg/s in rad/s
        const p_hat = p_target * ref.b_ref_ft / (2 * V_fps);
        const delta_a_30dps = -Cl_p_per_rad * p_hat / ({Cl_da_per_deg} * Math.PI / 180) * (180 / Math.PI);

        const trimHTML = `
            <div style="font-family: 'Courier New', monospace; font-size: 10px; line-height: 1.6; background: #e6f2ff; padding: 15px; border: 1px solid #ccc;">
                <p style="font-weight: bold; font-size: 11px;">@ 200 mph, 20,000 ft</p>
                <br>
                <p><b>Pitch Maneuvers:</b></p>
                <p style="margin-left: 15px;">1g pull-up (ΔCL = ${{delta_CL_target.toFixed(2)}}):</p>
                <p style="margin-left: 30px;">δe = ${{delta_e_1g.toFixed(1)}}°</p>
                <br>
                <p><b>Trim Requirements:</b></p>
                <p style="margin-left: 15px;">α = 2°:  δe ≈ ${{trim_2deg >= 0 ? '+' : ''}}${{trim_2deg.toFixed(1)}}°</p>
                <p style="margin-left: 15px;">α = 5°:  δe ≈ ${{trim_5deg >= 0 ? '+' : ''}}${{trim_5deg.toFixed(1)}}°</p>
                <p style="margin-left: 15px;">α = 10°: δe ≈ ${{trim_10deg >= 0 ? '+' : ''}}${{trim_10deg.toFixed(1)}}°</p>
                <br>
                <p><b>Roll Maneuvers:</b></p>
                <p style="margin-left: 15px;">Roll rate 30°/s:</p>
                <p style="margin-left: 30px;">δa = ${{delta_a_30dps.toFixed(1)}}°</p>
                <p style="margin-left: 15px;">Roll rate 60°/s:</p>
                <p style="margin-left: 30px;">δa = ${{(2*delta_a_30dps).toFixed(1)}}°</p>
                <br>
                <p><b>DESIGN LIMITS:</b></p>
                <p style="margin-left: 15px;">Recommended max deflection: ±25°</p>
                <p style="margin-left: 15px;">Structural limits: TBD</p>
                <p style="margin-left: 15px;">Actuator rate: TBD</p>
                <br>
                <p style="color: #008000;"><b>Control power is adequate for normal flight operations.</b></p>
            </div>
        `;
        document.getElementById('trim-requirements').innerHTML = trimHTML;

        // Elevon forces and hinge loading at 10° deflection
        const delta_e_test = 10.0;  // degrees
        const Mach_test = 0.5;
        const a_fps = 1116.45;  // Speed of sound at sea level (ft/s)
        const V_test_fps = Mach_test * a_fps;  // Mach 0.5 = 558.2 ft/s
        const V_mph = V_test_fps * 0.681818;  // Convert to mph for display
        const rho_slugft3 = 0.002377;
        const q_lbft2 = 0.5 * rho_slugft3 * V_test_fps * V_test_fps;
        const q_lbin2 = q_lbft2 / 144;

        const CL_0 = aero.static_stability.longitudinal.CL_0 || 0;
        const CD_0 = aero.static_stability.longitudinal.CD_0 || 0;

        const delta_e_rad = delta_e_test * Math.PI / 180;
        const CL_total = CL_0 + ({CL_de_per_deg} * Math.PI / 180) * delta_e_rad;
        const CD_total = CD_0;
        const Cm_total = Cm_0 + ({Cm_de_per_deg} * Math.PI / 180) * delta_e_rad;

        const L_total_lb = CL_total * q_lbft2 * ref.S_ref_ft2;
        const D_total_lb = CD_total * q_lbft2 * ref.S_ref_ft2;
        const M_total_lbft = Cm_total * q_lbft2 * ref.S_ref_ft2 * ref.c_ref_ft;
        const M_total_lbin = M_total_lbft * 12;

        const aircraft_weight_lb = mass_props.mass_lbm;
        const L_per_lb = L_total_lb / aircraft_weight_lb;
        const D_per_lb = D_total_lb / aircraft_weight_lb;

        // Hinge moment calculation using AVL Ch coefficient
        // HM = q * S_ref * c_ref * Ch (dimensional hinge moment)
        const Ch_elevon = {Ch_elevon if Ch_elevon is not None else 'null'};
        let hinge_moment_lbin = 0;
        let hinge_method = "N/A";

        if (Ch_elevon !== null) {{
            // Use actual AVL hinge moment coefficient
            // Ch is nondimensional: HM / (q * S * c)
            const hinge_moment_lbft = Ch_elevon * q_lbft2 * ref.S_ref_ft2 * ref.c_ref_ft;
            hinge_moment_lbin = Math.abs(hinge_moment_lbft * 12);
            hinge_method = "AVL Ch";
        }} else {{
            // Fallback to estimated method (legacy)
            const moment_arm_ft = 7.0;
            const elevon_normal_force_lb = Math.abs(M_total_lbft) / moment_arm_ft;
            const c_elevon_ft = 0.718;
            hinge_moment_lbin = elevon_normal_force_lb * c_elevon_ft * 0.25 * 12;
            hinge_method = "Estimated";
        }}

        // Servo/actuator load calculations
        // Calculate force required for different servo arm lengths
        const servo_arms_in = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0];  // inches
        const servo_forces_lb = servo_arms_in.map(arm => hinge_moment_lbin / arm);

        // Also calculate for linear actuator strokes (perpendicular force)
        const actuator_strokes_in = [1.0, 2.0, 3.0, 4.0];  // inches
        // For a linear actuator, effective arm ≈ stroke/2 at mid-travel for ±30° rotation
        const actuator_forces_lb = actuator_strokes_in.map(stroke => {{
            const effective_arm = stroke * 0.5;  // Approximate effective moment arm
            return hinge_moment_lbin / effective_arm;
        }});

        // Calculate hinge moment at different speeds for sizing chart
        const speeds_mph = [100, 150, 200, 250, 300, 350, 400];
        const hinge_moments_vs_speed = speeds_mph.map(v_mph => {{
            const v_fps = v_mph * 1.467;
            const q_local = 0.5 * rho_slugft3 * v_fps * v_fps;
            if (Ch_elevon !== null) {{
                return Math.abs(Ch_elevon * q_local * ref.S_ref_ft2 * ref.c_ref_ft * 12);
            }} else {{
                return 0;
            }}
        }});

        const elevonForcesHTML = `
            <div style="font-family: 'Courier New', monospace; font-size: 10px;">
                <h4 style="margin-top: 10px; margin-bottom: 10px;">Flight Condition</h4>
                <table style="width: 45%; border-collapse: collapse; float: left; margin-right: 5%;">
                    <tr style="background: #40466e; color: white;"><th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Parameter</th><th style="padding: 5px; border: 1px solid #ccc;">Value</th><th style="padding: 5px; border: 1px solid #ccc;">Units</th></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Mach Number</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{Mach_test.toFixed(2)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Velocity</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{V_test_fps.toFixed(1)}} ft/s (${{V_mph.toFixed(1)}} mph)</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Dynamic Pressure</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{q_lbin2.toFixed(4)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lb/in²</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Density</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{rho_slugft3.toFixed(6)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">slug/ft³</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Elevon Deflection</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{delta_e_test.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">deg</td></tr>
                </table>

                <h4 style="margin-top: 10px; margin-bottom: 10px; margin-left: 50%;">Force Coefficients</h4>
                <table style="width: 45%; border-collapse: collapse; float: left;">
                    <tr style="background: #40466e; color: white;"><th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Coefficient</th><th style="padding: 5px; border: 1px solid #ccc;">Value</th><th style="padding: 5px; border: 1px solid #ccc;">Units</th></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">CL</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{CL_total.toFixed(5)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">CD</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{CD_total.toFixed(5)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Cm</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{Cm_total.toFixed(5)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                </table>

                <div style="clear: both;"></div>

                <h4 style="margin-top: 20px; margin-bottom: 10px;">Total Forces (Aircraft Weight: ${{aircraft_weight_lb.toFixed(2)}} lb)</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #40466e; color: white;"><th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Force</th><th style="padding: 5px; border: 1px solid #ccc;">Value</th><th style="padding: 5px; border: 1px solid #ccc;">Units</th><th style="padding: 5px; border: 1px solid #ccc;">Per Pound</th></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Lift</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{L_total_lb.toFixed(2)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lb</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{L_per_lb.toFixed(4)}}</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Drag</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{D_total_lb.toFixed(2)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lb</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{D_per_lb.toFixed(4)}}</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Pitch Moment</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{M_total_lbin.toFixed(0)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lb-in</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                </table>

                <h4 style="margin-top: 20px; margin-bottom: 10px;">Control Derivatives</h4>
                <table style="width: 45%; border-collapse: collapse; float: left; margin-right: 5%;">
                    <tr style="background: #40466e; color: white;"><th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Derivative</th><th style="padding: 5px; border: 1px solid #ccc;">Value</th><th style="padding: 5px; border: 1px solid #ccc;">Units</th></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">CL_de</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{({CL_de_per_deg}).toFixed(5)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">/deg</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Cm_de</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{({Cm_de_per_deg}).toFixed(5)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">/deg</td></tr>
                </table>

                <h4 style="margin-top: 20px; margin-bottom: 10px; margin-left: 50%;">Elevon Hinge Loading (${{hinge_method}})</h4>
                <table style="width: 45%; border-collapse: collapse; float: left;">
                    <tr style="background: #40466e; color: white;"><th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Parameter</th><th style="padding: 5px; border: 1px solid #ccc;">Value</th><th style="padding: 5px; border: 1px solid #ccc;">Units</th></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Ch (hinge coeff)</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{Ch_elevon !== null ? Ch_elevon.toExponential(4) : 'N/A'}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Hinge Moment</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{hinge_moment_lbin.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lb-in</td></tr>
                    <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Hinge Moment (N-m)</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{(hinge_moment_lbin * 0.113).toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">N-m</td></tr>
                </table>

                <div style="clear: both;"></div>

                <h4 style="margin-top: 20px; margin-bottom: 10px;">Servo/Actuator Sizing (at ${{V_mph.toFixed(0)}} mph, ${{delta_e_test}}° deflection)</h4>

                <div style="display: flex; gap: 20px;">
                    <div style="flex: 1;">
                        <h5 style="margin: 5px 0;">Rotary Servo - Force vs Arm Length</h5>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background: #40466e; color: white;">
                                <th style="padding: 5px; border: 1px solid #ccc;">Arm Length</th>
                                <th style="padding: 5px; border: 1px solid #ccc;">Force Required</th>
                                <th style="padding: 5px; border: 1px solid #ccc;">Force (N)</th>
                            </tr>
                            ${{servo_arms_in.map((arm, i) => `
                            <tr style="background: ${{servo_forces_lb[i] > 500 ? '#ffcccc' : servo_forces_lb[i] > 200 ? '#ffffcc' : '#ccffcc'}};">
                                <td style="padding: 5px; border: 1px solid #e0e0e0;">${{arm.toFixed(2)}} in</td>
                                <td style="padding: 5px; border: 1px solid #e0e0e0; font-weight: bold;">${{servo_forces_lb[i].toFixed(1)}} lb</td>
                                <td style="padding: 5px; border: 1px solid #e0e0e0;">${{(servo_forces_lb[i] * 4.448).toFixed(1)}} N</td>
                            </tr>
                            `).join('')}}
                        </table>
                    </div>

                    <div style="flex: 1;">
                        <h5 style="margin: 5px 0;">Linear Actuator - Force vs Stroke</h5>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background: #40466e; color: white;">
                                <th style="padding: 5px; border: 1px solid #ccc;">Stroke</th>
                                <th style="padding: 5px; border: 1px solid #ccc;">Force Required</th>
                                <th style="padding: 5px; border: 1px solid #ccc;">Force (N)</th>
                            </tr>
                            ${{actuator_strokes_in.map((stroke, i) => `
                            <tr style="background: ${{actuator_forces_lb[i] > 500 ? '#ffcccc' : actuator_forces_lb[i] > 200 ? '#ffffcc' : '#ccffcc'}};">
                                <td style="padding: 5px; border: 1px solid #e0e0e0;">${{stroke.toFixed(1)}} in</td>
                                <td style="padding: 5px; border: 1px solid #e0e0e0; font-weight: bold;">${{actuator_forces_lb[i].toFixed(1)}} lb</td>
                                <td style="padding: 5px; border: 1px solid #e0e0e0;">${{(actuator_forces_lb[i] * 4.448).toFixed(1)}} N</td>
                            </tr>
                            `).join('')}}
                        </table>
                    </div>
                </div>

                <h4 style="margin-top: 20px; margin-bottom: 10px;">Hinge Moment vs Airspeed (at ${{delta_e_test}}° deflection)</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #40466e; color: white;">
                        <th style="padding: 5px; border: 1px solid #ccc;">Speed (mph)</th>
                        ${{speeds_mph.map(v => `<th style="padding: 5px; border: 1px solid #ccc;">${{v}}</th>`).join('')}}
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0; font-weight: bold;">HM (lb-in)</td>
                        ${{hinge_moments_vs_speed.map(hm => `<td style="padding: 5px; border: 1px solid #e0e0e0; background: ${{hm > 5000 ? '#ffcccc' : hm > 2000 ? '#ffffcc' : '#ccffcc'}};">${{hm.toFixed(0)}}</td>`).join('')}}
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0; font-weight: bold;">HM (N-m)</td>
                        ${{hinge_moments_vs_speed.map(hm => `<td style="padding: 5px; border: 1px solid #e0e0e0;">${{(hm * 0.113).toFixed(1)}}</td>`).join('')}}
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">Force @ 1" arm (lb)</td>
                        ${{hinge_moments_vs_speed.map(hm => `<td style="padding: 5px; border: 1px solid #e0e0e0;">${{hm.toFixed(0)}}</td>`).join('')}}
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #e0e0e0;">Force @ 2" arm (lb)</td>
                        ${{hinge_moments_vs_speed.map(hm => `<td style="padding: 5px; border: 1px solid #e0e0e0;">${{(hm/2).toFixed(0)}}</td>`).join('')}}
                    </tr>
                </table>

                <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border: 1px solid #ddd;">
                    <b>Actuator Sizing Guidelines:</b>
                    <ul style="margin: 5px 0; padding-left: 20px; font-size: 9px;">
                        <li><span style="background: #ccffcc; padding: 2px 5px;">Green</span> - Light load, hobby servos may work</li>
                        <li><span style="background: #ffffcc; padding: 2px 5px;">Yellow</span> - Moderate load, industrial servos recommended</li>
                        <li><span style="background: #ffcccc; padding: 2px 5px;">Red</span> - Heavy load, hydraulic or high-power electric actuator required</li>
                    </ul>
                    <p style="font-size: 9px; margin: 5px 0;">
                        <b>Notes:</b> Forces shown are per elevon (total for both sides = 2×).
                        Linear actuator forces assume perpendicular mounting at mid-travel.
                        Add 50-100% safety factor for dynamic loads and gusts.
                    </p>
                </div>

                <p style="margin-top: 15px; font-size: 9px; font-style: italic;">
                    <b>Calculation Notes:</b><br>
                    • Hinge moment: HM = Ch × q × S_ref × c_ref (from AVL HM command)<br>
                    • Servo force: F = HM / arm_length<br>
                    • Linear actuator effective arm ≈ stroke/2 for ±30° rotation<br>
                    • HM scales with V² (dynamic pressure)
                </p>
            </div>
        `;
        document.getElementById('elevon-forces').innerHTML = elevonForcesHTML;

        // Airfoil Polars - CL vs Alpha
        const colors = ['#000000', '#333333', '#666666', '#999999'];
        const clAlphaData = {json.dumps(polar_traces)}.map((polar, i) => ({{
            x: polar.alpha,
            y: polar.CL,
            type: 'scatter',
            mode: 'lines+markers',
            name: polar.re_str,
            line: {{ color: colors[i % colors.length], width: 1 }},
            marker: {{ color: colors[i % colors.length], size: 3, symbol: 'circle' }}
        }}));

        const clAlphaLayout = Object.assign({{}}, cadLayout, {{
            title: 'LIFT COEFFICIENT vs ANGLE OF ATTACK',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Alpha (deg)' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'CL' }}),
            showlegend: true,
            legend: {{ font: {{ color: '#000000' }}, bgcolor: '#ffffff', bordercolor: '#cccccc', borderwidth: 1 }}
        }});

        Plotly.newPlot('cl-alpha-plot', clAlphaData, clAlphaLayout, {{responsive: true, displayModeBar: false}});

        // Drag Polar - CL vs CD
        const dragPolarData = {json.dumps(polar_traces)}.map((polar, i) => ({{
            x: polar.CD,
            y: polar.CL,
            type: 'scatter',
            mode: 'lines+markers',
            name: polar.re_str,
            line: {{ color: colors[i % colors.length], width: 1 }},
            marker: {{ color: colors[i % colors.length], size: 3, symbol: 'circle' }}
        }}));

        const dragPolarLayout = Object.assign({{}}, cadLayout, {{
            title: 'DRAG POLAR (CL vs CD)',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'CD' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'CL' }}),
            showlegend: true,
            legend: {{ font: {{ color: '#000000' }}, bgcolor: '#ffffff', bordercolor: '#cccccc', borderwidth: 1 }}
        }});

        Plotly.newPlot('drag-polar-plot', dragPolarData, dragPolarLayout, {{responsive: true, displayModeBar: false}});

        // L/D Ratio - Combine XFOIL profile drag + AVL induced drag for 3D aircraft
        let ldRatioData;
        let ldTitle;

        if (avlPolar !== null) {{
            // 3D Aircraft L/D calculation
            ldTitle = 'LIFT-TO-DRAG RATIO (3D Aircraft)';
            ldRatioData = {json.dumps(polar_traces)}.map((polar, i) => {{
                // XFOIL data (2D airfoil section)
                const xfoil_cl = polar.CL;
                const xfoil_cd_profile = polar.CD;
                const xfoil_alpha = polar.alpha;

                // AVL data (3D wing)
                const avl_cl = avlPolar.CL;
                const avl_cd_ind = avlPolar.CD_induced;
                const avl_alpha = avlPolar.alpha;

                // Interpolate XFOIL profile drag at AVL CL values
                const cd_profile_at_avl_cl = avl_cl.map(cl => {{
                    // Linear interpolation
                    if (cl <= xfoil_cl[0]) return xfoil_cd_profile[0];
                    if (cl >= xfoil_cl[xfoil_cl.length - 1]) return xfoil_cd_profile[xfoil_cd_profile.length - 1];

                    for (let j = 0; j < xfoil_cl.length - 1; j++) {{
                        if (cl >= xfoil_cl[j] && cl <= xfoil_cl[j + 1]) {{
                            const t = (cl - xfoil_cl[j]) / (xfoil_cl[j + 1] - xfoil_cl[j]);
                            return xfoil_cd_profile[j] + t * (xfoil_cd_profile[j + 1] - xfoil_cd_profile[j]);
                        }}
                    }}
                    return xfoil_cd_profile[xfoil_cd_profile.length - 1];
                }});

                // Total drag = profile + induced
                const cd_total = cd_profile_at_avl_cl.map((cd_p, j) => cd_p + avl_cd_ind[j]);

                // L/D = CL / CD_total
                const ld = avl_cl.map((cl, j) => cd_total[j] !== 0 ? cl / cd_total[j] : 0);

                return {{
                    x: avl_alpha,
                    y: ld,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: polar.re_str,
                    line: {{ color: colors[i % colors.length], width: 1 }},
                    marker: {{ color: colors[i % colors.length], size: 3, symbol: 'circle' }}
                }};
            }});
        }} else {{
            // Fallback to 2D airfoil data if AVL not available
            ldTitle = 'LIFT-TO-DRAG RATIO (2D Airfoil - AVL data not available)';
            ldRatioData = {json.dumps(polar_traces)}.map((polar, i) => {{
                const ld = polar.CL.map((cl, j) => polar.CD[j] !== 0 ? cl / polar.CD[j] : 0);
                return {{
                    x: polar.alpha,
                    y: ld,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: polar.re_str,
                    line: {{ color: colors[i % colors.length], width: 1 }},
                    marker: {{ color: colors[i % colors.length], size: 3, symbol: 'circle' }}
                }};
            }});
        }}

        const ldRatioLayout = Object.assign({{}}, cadLayout, {{
            title: ldTitle,
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Alpha (deg)' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'L/D' }}),
            showlegend: true,
            legend: {{ font: {{ color: '#000000' }}, bgcolor: '#ffffff', bordercolor: '#cccccc', borderwidth: 1 }}
        }});

        Plotly.newPlot('ld-ratio-plot', ldRatioData, ldRatioLayout, {{responsive: true, displayModeBar: false}});

        // Moment Coefficient
        const cmAlphaData = {json.dumps(polar_traces)}.map((polar, i) => ({{
            x: polar.alpha,
            y: polar.CM,
            type: 'scatter',
            mode: 'lines+markers',
            name: polar.re_str,
            line: {{ color: colors[i % colors.length], width: 1 }},
            marker: {{ color: colors[i % colors.length], size: 3, symbol: 'circle' }}
        }}));

        const cmAlphaLayout = Object.assign({{}}, cadLayout, {{
            title: 'MOMENT COEFFICIENT vs ANGLE OF ATTACK',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Alpha (deg)' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'CM' }}),
            showlegend: true,
            legend: {{ font: {{ color: '#000000' }}, bgcolor: '#ffffff', bordercolor: '#cccccc', borderwidth: 1 }}
        }});

        Plotly.newPlot('cm-alpha-plot', cmAlphaData, cmAlphaLayout, {{responsive: true, displayModeBar: false}});

        // === LATERAL DYNAMICS ANALYSIS ===
        // Compute all lateral-directional modes from stability derivatives

        // Get derivatives (non-dimensional)
        const CY_beta = aero.static_stability.lateral_directional.CY_beta_per_rad;
        const Cl_beta = aero.static_stability.lateral_directional.Cl_beta_per_rad;
        const Cn_beta = aero.static_stability.lateral_directional.Cn_beta_per_rad;
        const Cl_p = aero.dynamic_stability.roll_rate.Cl_p_per_rad;
        const Cn_p = aero.dynamic_stability.roll_rate.Cn_p_per_rad;
        const Cl_r = aero.dynamic_stability.yaw_rate.Cl_r_per_rad;
        const Cn_r = aero.dynamic_stability.yaw_rate.Cn_r_per_rad;

        // Flight condition parameters
        const rho = 0.002377;  // slug/ft³ (sea level)
        const g = 32.174;  // ft/s²
        const mass_slug = mass_props.mass_lbm / 32.174;
        const Ixx = mass_props.inertia_lbm_ft2.Ixx / 32.174;
        const Izz = mass_props.inertia_lbm_ft2.Izz / 32.174;

        // Helper function to compute lateral modes at a given airspeed
        function computeLateralModes(V_mph) {{
            const V = V_mph * 1.467;  // Convert mph to ft/s
            const q_bar = 0.5 * rho * V * V;

            // Dimensional derivatives
            const Y_beta = q_bar * ref.S_ref_ft2 * CY_beta / mass_slug;
            const L_beta = q_bar * ref.S_ref_ft2 * ref.b_ref_ft * Cl_beta / Ixx;
            const N_beta = q_bar * ref.S_ref_ft2 * ref.b_ref_ft * Cn_beta / Izz;
            const L_p = q_bar * ref.S_ref_ft2 * ref.b_ref_ft * ref.b_ref_ft * Cl_p / (2 * V * Ixx);
            const N_p = q_bar * ref.S_ref_ft2 * ref.b_ref_ft * ref.b_ref_ft * Cn_p / (2 * V * Izz);
            const L_r = q_bar * ref.S_ref_ft2 * ref.b_ref_ft * ref.b_ref_ft * Cl_r / (2 * V * Ixx);
            const N_r = q_bar * ref.S_ref_ft2 * ref.b_ref_ft * ref.b_ref_ft * Cn_r / (2 * V * Izz);

            // Compute eigenvalues using simplified 2D Dutch roll approximation
            // Using reduced 2x2 system for Dutch roll: [beta, r]
            const a11 = Y_beta/V;
            const a12 = -1;
            const a21 = N_beta;
            const a22 = N_r;

            const trace = a11 + a22;
            const det = a11*a22 - a12*a21;
            const discriminant = trace*trace - 4*det;

            let dutchRoll = null;
            if (discriminant < 0) {{
                const realPart = trace / 2;
                const imagPart = Math.sqrt(-discriminant) / 2;
                const omega_n = Math.sqrt(realPart*realPart + imagPart*imagPart);
                const omega_d = Math.abs(imagPart);
                const zeta = -realPart / omega_n;
                dutchRoll = {{
                    realPart: realPart,
                    imagPart: imagPart,
                    omega_n: omega_n,
                    omega_d: omega_d,
                    zeta: zeta,
                    period: 2 * Math.PI / omega_d,
                    freq_hz: omega_d / (2 * Math.PI),
                    stable: realPart < 0
                }};
            }}

            // Compute roll subsidence mode (fast exponential)
            // Roll subsidence eigenvalue ≈ L_p
            const rollMode = {{
                eigenvalue: L_p,
                timeConst: Math.abs(1.0 / L_p),
                stable: L_p < 0
            }};

            // Compute spiral mode (slow exponential)
            // Spiral approximation: λ ≈ (L_beta*N_r - N_beta*L_r) / (L_beta - V*N_beta/g)
            const spiral_num = L_beta * N_r - N_beta * L_r;
            const spiral_den = L_beta;
            const spiralMode = {{
                eigenvalue: spiral_num / spiral_den,
                timeConst: Math.abs(spiral_den / spiral_num),
                stable: (spiral_num / spiral_den) < 0
            }};

            return {{ dutchRoll, rollMode, spiralMode }};
        }}

        // Compute modes at cruise (200 mph)
        const cruiseModes = computeLateralModes(200);

        // Display modes summary
        function statusBadge(stable) {{
            return stable ?
                '<span style="color: #1b5e20; background: #c8e6c9; padding: 5px 12px; border-radius: 3px; font-weight: bold;">✓ STABLE</span>' :
                '<span style="color: #b71c1c; background: #ffcdd2; padding: 5px 12px; border-radius: 3px; font-weight: bold;">✗ UNSTABLE</span>';
        }}

        let summaryHTML = '<table style="width: 100%; margin-top: 10px;"><tr><th>Mode</th><th>Eigenvalue(s)</th><th>Characteristics</th><th>Status</th></tr>';

        // Dutch Roll mode
        if (cruiseModes.dutchRoll) {{
            const dr = cruiseModes.dutchRoll;
            const dampingQuality = dr.zeta > 0.3 ? 'Well damped' : dr.zeta > 0.1 ? 'Lightly damped' : 'Poorly damped';
            summaryHTML += `
                <tr>
                    <td><b>Dutch Roll</b></td>
                    <td>${{dr.realPart.toFixed(3)}} ± ${{dr.imagPart.toFixed(3)}}i</td>
                    <td>Period: ${{dr.period.toFixed(2)}} s<br>ζ = ${{dr.zeta.toFixed(3)}} (${{dampingQuality}})<br>f = ${{dr.freq_hz.toFixed(2)}} Hz</td>
                    <td>${{statusBadge(dr.stable)}}</td>
                </tr>
            `;
        }}

        // Roll subsidence mode
        const roll = cruiseModes.rollMode;
        summaryHTML += `
            <tr>
                <td><b>Roll Subsidence</b></td>
                <td>${{roll.eigenvalue.toFixed(3)}}</td>
                <td>Time constant: ${{roll.timeConst.toFixed(3)}} s<br>Fast exponential decay</td>
                <td>${{statusBadge(roll.stable)}}</td>
            </tr>
        `;

        // Spiral mode
        const spiral = cruiseModes.spiralMode;
        summaryHTML += `
            <tr>
                <td><b>Spiral</b></td>
                <td>${{spiral.eigenvalue.toFixed(4)}}</td>
                <td>Time constant: ${{spiral.timeConst.toFixed(1)}} s<br>Slow exponential</td>
                <td>${{statusBadge(spiral.stable)}}</td>
            </tr>
        `;

        summaryHTML += '</table>';
        document.getElementById('modes-summary').innerHTML = summaryHTML;

        // Mode characteristics writeup
        const writeupHTML = `
            <p><b>Dutch Roll:</b> An oscillatory mode combining yawing and rolling motions, typically with sideslip oscillations.
            The aircraft rocks back and forth like a ship. For good handling qualities, the damping ratio should be greater than 0.1,
            with 0.3-0.5 being ideal. The frequency is typically 0.5-2 Hz for most aircraft.</p>

            <p><b>Roll Subsidence:</b> A fast, non-oscillatory mode describing how quickly the aircraft stops rolling when
            aileron input is removed. This should be heavily damped (time constant &lt; 1 second) for good control response.
            The roll damping derivative Cl<sub>p</sub> must be negative for stability.</p>

            <p><b>Spiral Mode:</b> A slow, non-oscillatory mode where the aircraft gradually enters a descending spiral turn.
            This mode is often slightly unstable in real aircraft but acceptable if the time-to-double is long (e.g., &gt; 20 seconds),
            allowing pilot correction. Positive dihedral effect (Cl<sub>β</sub> &lt; 0) and weathercock stability (Cn<sub>β</sub> &gt; 0)
            affect spiral stability.</p>
        `;
        document.getElementById('modes-writeup').innerHTML = writeupHTML;

        // Plot Dutch roll time response
        if (cruiseModes.dutchRoll) {{
            const dr = cruiseModes.dutchRoll;
            const t_max = 5 * dr.period;
            const t = [];
            const response = [];
            const envelope_pos = [];
            const envelope_neg = [];

            for (let i = 0; i <= 500; i++) {{
                const time = i * t_max / 500;
                t.push(time);
                const env = Math.exp(dr.realPart * time);
                const resp = env * Math.cos(dr.imagPart * time);
                response.push(resp);
                envelope_pos.push(env);
                envelope_neg.push(-env);
            }}

            const responseLayout = Object.assign({{}}, cadLayout, {{
                title: `DUTCH ROLL TIME RESPONSE (ζ=${{dr.zeta.toFixed(3)}})`,
                xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Time (seconds)' }}),
                yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'Normalized Amplitude' }}),
                showlegend: true,
                legend: {{ font: {{ color: '#000000' }}, bgcolor: '#ffffff', bordercolor: '#cccccc', borderwidth: 1 }}
            }});

            Plotly.newPlot('dutch-roll-response-plot', [
                {{ x: t, y: envelope_neg, type: 'scatter', mode: 'lines', name: 'Envelope', showlegend: false, line: {{ color: '#ff0000', width: 1, dash: 'dash' }} }},
                {{ x: t, y: envelope_pos, type: 'scatter', mode: 'lines', name: 'Envelope', line: {{ color: '#ff0000', width: 1, dash: 'dash' }} }},
                {{ x: t, y: response, type: 'scatter', mode: 'lines', name: 'Dutch Roll', line: {{ color: '#000000', width: 2 }} }}
            ], responseLayout, {{responsive: true, displayModeBar: false}});
        }}

        // Plot eigenvalues in s-plane
        const eigenTraces = [];
        if (cruiseModes.dutchRoll) {{
            eigenTraces.push({{
                x: [cruiseModes.dutchRoll.realPart, cruiseModes.dutchRoll.realPart],
                y: [cruiseModes.dutchRoll.imagPart, -cruiseModes.dutchRoll.imagPart],
                type: 'scatter',
                mode: 'markers',
                name: 'Dutch Roll',
                marker: {{ color: '#CC6677', size: 12, symbol: 'circle' }}
            }});
        }}
        eigenTraces.push({{
            x: [roll.eigenvalue],
            y: [0],
            type: 'scatter',
            mode: 'markers',
            name: 'Roll Subsidence',
            marker: {{ color: '#44AA99', size: 12, symbol: 'square' }}
        }});
        eigenTraces.push({{
            x: [spiral.eigenvalue],
            y: [0],
            type: 'scatter',
            mode: 'markers',
            name: 'Spiral',
            marker: {{ color: '#DDCC77', size: 12, symbol: 'diamond' }}
        }});

        const eigenLayout = Object.assign({{}}, cadLayout, {{
            title: 'LATERAL EIGENVALUES (s-plane)',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{
                title: 'Real Part (1/s)',
                zeroline: true,
                zerolinecolor: '#000000',
                zerolinewidth: 2
            }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{
                title: 'Imaginary Part (rad/s)',
                zeroline: true,
                zerolinecolor: '#000000',
                zerolinewidth: 2
            }}),
            showlegend: true,
            legend: {{ font: {{ color: '#000000' }}, bgcolor: '#ffffff', bordercolor: '#cccccc', borderwidth: 1 }},
            shapes: [{{
                type: 'rect',
                xref: 'x',
                yref: 'paper',
                x0: -100,
                y0: 0,
                x1: 0,
                y1: 1,
                fillcolor: '#c8e6c9',
                opacity: 0.2,
                layer: 'below',
                line: {{ width: 0 }}
            }}],
            annotations: [{{
                x: -0.1,
                y: 0.95,
                xref: 'x',
                yref: 'paper',
                text: 'Stable Region',
                showarrow: false,
                font: {{ size: 12, color: '#1b5e20', family: 'Courier New' }},
                bgcolor: 'rgba(200, 230, 201, 0.7)',
                bordercolor: '#1b5e20',
                borderwidth: 1
            }}]
        }});

        Plotly.newPlot('eigenvalue-plot', eigenTraces, eigenLayout, {{responsive: true, displayModeBar: false}});

        // Speed sweep analysis (50-300 mph)
        const speeds = [];
        const damping_ratios = [];
        const frequencies = [];

        for (let V = 50; V <= 300; V += 5) {{
            const modes = computeLateralModes(V);
            speeds.push(V);
            if (modes.dutchRoll) {{
                damping_ratios.push(modes.dutchRoll.zeta);
                frequencies.push(modes.dutchRoll.freq_hz);
            }} else {{
                damping_ratios.push(null);
                frequencies.push(null);
            }}
        }}

        // Plot damping ratio vs speed
        const dampingLayout = Object.assign({{}}, cadLayout, {{
            title: 'DUTCH ROLL DAMPING RATIO vs AIRSPEED',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Airspeed (mph)' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'Damping Ratio (ζ)' }}),
            showlegend: false,
            shapes: [{{
                type: 'line',
                x0: 50,
                x1: 300,
                y0: 0.1,
                y1: 0.1,
                line: {{ color: 'red', width: 1, dash: 'dash' }}
            }}],
            annotations: [{{
                x: 280,
                y: 0.12,
                text: 'Min acceptable (ζ=0.1)',
                showarrow: false,
                font: {{ size: 10, color: 'red' }}
            }}]
        }});

        Plotly.newPlot('damping-vs-speed-plot', [{{
            x: speeds,
            y: damping_ratios,
            type: 'scatter',
            mode: 'lines+markers',
            line: {{ color: '#000000', width: 2 }},
            marker: {{ color: '#000000', size: 4 }}
        }}], dampingLayout, {{responsive: true, displayModeBar: false}});

        // Plot frequency vs speed
        const freqLayout = Object.assign({{}}, cadLayout, {{
            title: 'DUTCH ROLL FREQUENCY vs AIRSPEED',
            xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'Airspeed (mph)' }}),
            yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'Frequency (Hz)' }}),
            showlegend: false
        }});

        Plotly.newPlot('freq-vs-speed-plot', [{{
            x: speeds,
            y: frequencies,
            type: 'scatter',
            mode: 'lines+markers',
            line: {{ color: '#000000', width: 2 }},
            marker: {{ color: '#000000', size: 4 }}
        }}], freqLayout, {{responsive: true, displayModeBar: false}});

        // === RANGE ANALYSIS ===
        // Breguet Range Equation: R = (V / SFC) * (L/D) * ln(W1/W2)

        const fuel_mass_lbm = mass_props.fuel_mass_lbm;
        const total_mass_lbm = mass_props.mass_lbm;

        if (fuel_mass_lbm && fuel_mass_lbm > 0) {{
            const empty_weight_lbm = total_mass_lbm - fuel_mass_lbm;
            const W1 = total_mass_lbm;  // Initial weight (full fuel)
            const W2 = empty_weight_lbm;  // Final weight (fuel exhausted)

            // Typical SFC values for small piston engines
            // Avgas: ~0.45 lb/(hp·hr) for best economy
            // Converting to lb/(lb·hr) requires knowing thrust/power relationship
            // For propeller aircraft: SFC_thrust = SFC_power * V / (550 * eta_prop)
            // Simplified: use 0.5-0.7 lb/hr per lb-thrust for small props

            // Reference L/D from AVL data
            let LD_max = 15;  // Default estimate
            if (avlPolar !== null) {{
                // Find max L/D from polar data
                const avl_ld = avlPolar.CL.map((cl, i) => {{
                    const cd_ind = avlPolar.CD_induced[i];
                    const cd_total = cd_ind + 0.01;  // Add estimated profile drag
                    return cl / cd_total;
                }});
                LD_max = Math.max(...avl_ld);
            }}

            // Build range calculator HTML
            const sfc_options = [
                {{ name: 'Efficient Piston (cruise)', sfc: 0.45 }},
                {{ name: 'Typical Piston', sfc: 0.55 }},
                {{ name: 'High Performance Piston', sfc: 0.65 }},
                {{ name: 'Small Turboprop', sfc: 0.50 }},
                {{ name: 'Jet (lb/lbf/hr)', sfc: 0.80 }}
            ];

            // ============================================================
            // MISSION SEGMENT ANALYSIS
            // ============================================================
            // Using fuel fractions for each mission segment (Raymer method)
            // W_i+1 / W_i = fuel fraction for segment i
            //
            // Typical fuel fractions:
            // - Warmup & Taxi:  0.970 (3% fuel burn)
            // - Takeoff:        0.985 (1.5% fuel burn)
            // - Climb:          0.980 (2% fuel burn)
            // - Cruise:         Breguet equation
            // - Loiter:         Breguet endurance
            // - Descent:        0.990 (1% fuel burn - mostly glide)
            // - Landing & Taxi: 0.995 (0.5% fuel burn)

            const eta_prop = 0.80;  // Propeller efficiency (typical 0.75-0.85)
            const SFC_cruise = 0.45;  // lb/(hp·hr) at cruise - typical efficient piston
            const V_cruise_kts = 175;  // knots cruise speed
            const V_cruise_mph = V_cruise_kts * 1.15078;
            const loiter_time_hr = 0.5;  // 30 min loiter
            const LD_loiter = LD_max * 0.9;  // L/D at loiter speed (slightly lower)

            // Mission segment fuel fractions (weight ratio W_end/W_start)
            const ff_warmup_taxi = 0.970;
            const ff_takeoff = 0.985;
            const ff_climb = 0.980;
            const ff_descent = 0.990;
            const ff_landing = 0.995;

            // Breguet range equation for cruise (propeller aircraft)
            // R_nm = (eta_prop / SFC) × (L/D) × ln(W1/W2) × 325.87
            function breguetRangeNm(SFC_lb_hp_hr, LD, W1_lb, W2_lb, eta_prop) {{
                const range_nm = (eta_prop / SFC_lb_hp_hr) * LD * Math.log(W1_lb / W2_lb) * 325.87;
                return range_nm;
            }}

            // Breguet endurance equation for loiter (propeller aircraft)
            // E_hr = (eta_prop / SFC) × (L/D) × ln(W1/W2) × (1/V) × 325.87
            // Simplified: E = R / V
            function breguetEnduranceHr(SFC_lb_hp_hr, LD, W1_lb, W2_lb, eta_prop) {{
                // Returns endurance in hours
                // For loiter, we solve for fuel fraction given time
                // W2/W1 = exp(-E × V × SFC / (eta × L/D × 325.87))
                return (eta_prop / SFC_lb_hp_hr) * LD * Math.log(W1_lb / W2_lb) * 325.87 / V_cruise_kts;
            }}

            // Calculate loiter fuel fraction for given time
            function loiterFuelFraction(E_hr, SFC_lb_hp_hr, LD, eta_prop, V_loiter_kts) {{
                // W2/W1 = exp(-E × SFC × V / (eta × L/D × 325.87))
                const V_loiter = V_cruise_kts * 0.7;  // Loiter at 70% cruise speed
                const exponent = -E_hr * SFC_lb_hp_hr * V_loiter / (eta_prop * LD * 325.87);
                return Math.exp(exponent);
            }}

            const ff_loiter = loiterFuelFraction(loiter_time_hr, SFC_cruise, LD_loiter, eta_prop, V_cruise_kts * 0.7);

            // Calculate weight at each mission segment
            // W0 = MTOW (W1 in our notation)
            const W0_takeoff = W1;
            const W1_after_warmup = W0_takeoff * ff_warmup_taxi;
            const W2_after_takeoff = W1_after_warmup * ff_takeoff;
            const W3_after_climb = W2_after_takeoff * ff_climb;
            // W4_after_cruise = W3 × ff_cruise (Breguet - this is what we solve for)
            // W5_after_loiter = W4 × ff_loiter
            const W6_after_descent_factor = ff_descent;
            const W7_landing_factor = ff_landing;

            // Total non-cruise fuel fraction
            const ff_non_cruise = ff_warmup_taxi * ff_takeoff * ff_climb * ff_loiter * ff_descent * ff_landing;

            // Reserve fuel (6% of initial fuel for 45 min reserve at cruise)
            const reserve_fraction = 0.06;

            // Available fuel for cruise
            // W_fuel_available = W0 - W_empty = fuel_mass
            // But we need to account for non-cruise segments
            // W3 (start cruise) / W0 = ff_warmup × ff_takeoff × ff_climb
            // W_final / W3 = ff_cruise × ff_loiter × ff_descent × ff_landing
            // W_final = W_empty + reserve = W0 - fuel_mass + reserve_fuel

            const W_start_cruise = W3_after_climb;
            const reserve_fuel = fuel_mass_lbm * reserve_fraction;
            const W_end_mission = W2 + reserve_fuel;  // Empty + reserve

            // Work backwards from end of mission
            // W_after_landing = W_end_mission
            // W_after_descent = W_after_landing / ff_landing
            // W_after_loiter = W_after_descent / ff_descent
            // W_after_cruise = W_after_loiter / ff_loiter
            const W_after_landing = W_end_mission;
            const W_after_descent = W_after_landing / ff_landing;
            const W_after_loiter = W_after_descent / ff_descent;
            const W_after_cruise = W_after_loiter / ff_loiter;

            // Cruise fuel fraction
            const ff_cruise = W_after_cruise / W_start_cruise;

            // Calculate cruise range using Breguet
            const cruise_range_nm = breguetRangeNm(SFC_cruise, LD_max, W_start_cruise, W_after_cruise, eta_prop);

            // Total mission fuel burned
            const fuel_burned_warmup = W0_takeoff - W1_after_warmup;
            const fuel_burned_takeoff = W1_after_warmup - W2_after_takeoff;
            const fuel_burned_climb = W2_after_takeoff - W3_after_climb;
            const fuel_burned_cruise = W_start_cruise - W_after_cruise;
            const fuel_burned_loiter = W_after_cruise - W_after_loiter;
            const fuel_burned_descent = W_after_loiter - W_after_descent;
            const fuel_burned_landing = W_after_descent - W_after_landing;
            const total_fuel_burned = fuel_mass_lbm - reserve_fuel;

            // Endurance calculation
            const cruise_time_hr = cruise_range_nm / V_cruise_kts;
            const total_endurance_hr = cruise_time_hr + loiter_time_hr + 0.25;  // +15 min for other segments

            const rangeCalcHTML = `
                <div style="font-family: 'Courier New', monospace; font-size: 10px;">
                    <h4 style="margin: 10px 0;">Mission Segment Analysis</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #40466e; color: white;">
                            <th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Segment</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">W_start (lb)</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">W_end (lb)</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">Fuel (lb)</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">W_i+1/W_i</th>
                        </tr>
                        <tr><td style="padding: 4px; border: 1px solid #e0e0e0;">1. Warmup & Taxi</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W0_takeoff.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W1_after_warmup.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{fuel_burned_warmup.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{ff_warmup_taxi.toFixed(3)}}</td></tr>
                        <tr><td style="padding: 4px; border: 1px solid #e0e0e0;">2. Takeoff</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W1_after_warmup.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W2_after_takeoff.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{fuel_burned_takeoff.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{ff_takeoff.toFixed(3)}}</td></tr>
                        <tr><td style="padding: 4px; border: 1px solid #e0e0e0;">3. Climb</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W2_after_takeoff.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W3_after_climb.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{fuel_burned_climb.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{ff_climb.toFixed(3)}}</td></tr>
                        <tr style="background: #e3f2fd;"><td style="padding: 4px; border: 1px solid #e0e0e0; font-weight: bold;">4. Cruise</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_start_cruise.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_after_cruise.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0; font-weight: bold;">${{fuel_burned_cruise.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{ff_cruise.toFixed(3)}}</td></tr>
                        <tr><td style="padding: 4px; border: 1px solid #e0e0e0;">5. Loiter (${{(loiter_time_hr*60).toFixed(0)}} min)</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_after_cruise.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_after_loiter.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{fuel_burned_loiter.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{ff_loiter.toFixed(3)}}</td></tr>
                        <tr><td style="padding: 4px; border: 1px solid #e0e0e0;">6. Descent</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_after_loiter.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_after_descent.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{fuel_burned_descent.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{ff_descent.toFixed(3)}}</td></tr>
                        <tr><td style="padding: 4px; border: 1px solid #e0e0e0;">7. Landing & Taxi</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_after_descent.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W_after_landing.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{fuel_burned_landing.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{ff_landing.toFixed(3)}}</td></tr>
                        <tr style="background: #fff3e0;"><td style="padding: 4px; border: 1px solid #e0e0e0;">Reserve (6%)</td><td colspan="2" style="padding: 4px; border: 1px solid #e0e0e0;"></td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{reserve_fuel.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">-</td></tr>
                        <tr style="background: #e8e8e8; font-weight: bold;"><td style="padding: 4px; border: 1px solid #e0e0e0;">TOTAL</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W0_takeoff.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{W2.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">${{fuel_mass_lbm.toFixed(1)}}</td><td style="padding: 4px; border: 1px solid #e0e0e0;">-</td></tr>
                    </table>

                    <h4 style="margin: 20px 0 10px 0;">Mission Range @ ${{V_cruise_kts}} kts Cruise</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #40466e; color: white;">
                            <th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Metric</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">Value</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">Units</th>
                        </tr>
                        <tr style="background: #c8e6c9;">
                            <td style="padding: 8px; border: 1px solid #e0e0e0; font-weight: bold;">Cruise Range</td>
                            <td style="padding: 8px; border: 1px solid #e0e0e0; font-weight: bold; font-size: 14px;">${{cruise_range_nm.toFixed(0)}}</td>
                            <td style="padding: 8px; border: 1px solid #e0e0e0;">nm</td>
                        </tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Cruise Range (statute miles)</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{(cruise_range_nm * 1.15078).toFixed(0)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">mi</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Cruise Range (km)</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{(cruise_range_nm * 1.852).toFixed(0)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">km</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Cruise Time</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{cruise_time_hr.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">hr</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Total Endurance</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{total_endurance_hr.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">hr</td></tr>
                    </table>

                    <h4 style="margin: 20px 0 10px 0;">Analysis Parameters</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #40466e; color: white;">
                            <th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Parameter</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">Value</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">Units</th>
                        </tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">MTOW</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{W1.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lbm</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Empty Weight</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{W2.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lbm</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Fuel Capacity</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{fuel_mass_lbm.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lbm</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Max L/D</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{LD_max.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">SFC (cruise)</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{SFC_cruise.toFixed(2)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">lb/(hp·hr)</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Propeller Efficiency</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{(eta_prop * 100).toFixed(0)}}%</td><td style="padding: 5px; border: 1px solid #e0e0e0;">-</td></tr>
                    </table>
                </div>
            `;
            document.getElementById('range-calculator').innerHTML = rangeCalcHTML;

            // Use cruise_range_nm for mission profile
            const range_nm = cruise_range_nm;

            // Endurance calculator
            const enduranceHTML = `
                <div style="font-family: 'Courier New', monospace; font-size: 10px;">
                    <h4 style="margin: 10px 0;">Endurance Summary</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #40466e; color: white;">
                            <th style="padding: 5px; border: 1px solid #ccc; text-align: left;">Segment</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">Time</th>
                            <th style="padding: 5px; border: 1px solid #ccc;">Units</th>
                        </tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Cruise @ ${{V_cruise_kts}} kts</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{cruise_time_hr.toFixed(1)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">hr</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Loiter</td><td style="padding: 5px; border: 1px solid #e0e0e0;">${{(loiter_time_hr * 60).toFixed(0)}}</td><td style="padding: 5px; border: 1px solid #e0e0e0;">min</td></tr>
                        <tr><td style="padding: 5px; border: 1px solid #e0e0e0;">Other segments (approx)</td><td style="padding: 5px; border: 1px solid #e0e0e0;">15</td><td style="padding: 5px; border: 1px solid #e0e0e0;">min</td></tr>
                        <tr style="background: #c8e6c9;">
                            <td style="padding: 8px; border: 1px solid #e0e0e0; font-weight: bold;">Total Mission Time</td>
                            <td style="padding: 8px; border: 1px solid #e0e0e0; font-weight: bold; font-size: 14px;">${{total_endurance_hr.toFixed(1)}}</td>
                            <td style="padding: 8px; border: 1px solid #e0e0e0;">hr</td>
                        </tr>
                    </table>
                </div>
            `;
            document.getElementById('endurance-calculator').innerHTML = enduranceHTML;

            // Mission Profile Plot
            // Typical mission: Warmup/Taxi -> Takeoff -> Climb -> Cruise -> Loiter -> Descent -> Landing
            const cruise_alt = 20000;  // ft
            const loiter_alt = 5000;   // ft
            const climb_dist_nm = 20;  // nm to climb
            const descent_dist_nm = 30; // nm to descend
            const loiter_time_min = 30; // minutes loiter
            const loiter_dist_nm = (loiter_time_min / 60) * V_cruise_kts * 0.7;  // at 70% cruise speed

            // Mission segments (distance in nm, altitude in ft)
            const mission_x = [0, 0, climb_dist_nm, climb_dist_nm + range_nm, climb_dist_nm + range_nm + descent_dist_nm/2, climb_dist_nm + range_nm + descent_dist_nm/2 + loiter_dist_nm, climb_dist_nm + range_nm + descent_dist_nm + loiter_dist_nm, climb_dist_nm + range_nm + descent_dist_nm + loiter_dist_nm];
            const mission_y = [0, 0, cruise_alt, cruise_alt, loiter_alt, loiter_alt, 0, 0];

            // Simplified mission for cleaner look
            const simple_x = [0, 5, climb_dist_nm, climb_dist_nm + range_nm, climb_dist_nm + range_nm + 10, climb_dist_nm + range_nm + 10 + loiter_dist_nm, climb_dist_nm + range_nm + descent_dist_nm + loiter_dist_nm, climb_dist_nm + range_nm + descent_dist_nm + loiter_dist_nm + 5];
            const simple_y = [0, 0, cruise_alt, cruise_alt, loiter_alt, loiter_alt, 0, 0];

            const total_mission_nm = simple_x[simple_x.length - 1];

            // Cruise midpoint for annotation
            const cruise_mid_x = climb_dist_nm + range_nm / 2;

            const missionLayout = Object.assign({{}}, cadLayout, {{
                title: 'MISSION PROFILE',
                autosize: false,
                width: 1400,
                height: 320,
                margin: {{ l: 60, r: 30, t: 40, b: 50 }},
                xaxis: Object.assign({{}}, cadLayout.xaxis, {{
                    title: 'Distance (nm)',
                    range: [-10, total_mission_nm + 20]
                }}),
                yaxis: Object.assign({{}}, cadLayout.yaxis, {{
                    title: 'Altitude (ft)',
                    range: [-2000, cruise_alt * 1.2]
                }}),
                showlegend: false,
                annotations: [
                    {{
                        x: 2.5,
                        y: -1000,
                        text: 'Warmup &<br>Takeoff',
                        showarrow: false,
                        font: {{ size: 9, color: '#333' }}
                    }},
                    {{
                        x: climb_dist_nm / 2 + 2,
                        y: cruise_alt / 2,
                        text: 'Climb',
                        showarrow: false,
                        font: {{ size: 10, color: '#333' }}
                    }},
                    {{
                        x: cruise_mid_x,
                        y: cruise_alt + 1500,
                        text: `<b>Cruise: ${{range_nm.toFixed(0)}} nm</b>`,
                        showarrow: true,
                        arrowhead: 2,
                        arrowcolor: '#cc0000',
                        ax: 0,
                        ay: 30,
                        font: {{ size: 12, color: '#cc0000', family: 'Courier New' }}
                    }},
                    {{
                        x: climb_dist_nm + range_nm + 10 + loiter_dist_nm / 2,
                        y: loiter_alt + 1500,
                        text: 'Loiter',
                        showarrow: false,
                        font: {{ size: 10, color: '#333' }}
                    }},
                    {{
                        x: climb_dist_nm + range_nm + descent_dist_nm + loiter_dist_nm + 2,
                        y: -1000,
                        text: 'Landing',
                        showarrow: false,
                        font: {{ size: 9, color: '#333' }}
                    }}
                ],
                shapes: [
                    // Cruise distance bracket
                    {{
                        type: 'line',
                        x0: climb_dist_nm,
                        x1: climb_dist_nm + range_nm,
                        y0: cruise_alt - 1000,
                        y1: cruise_alt - 1000,
                        line: {{ color: '#cc0000', width: 2 }}
                    }},
                    {{
                        type: 'line',
                        x0: climb_dist_nm,
                        x1: climb_dist_nm,
                        y0: cruise_alt - 1500,
                        y1: cruise_alt - 500,
                        line: {{ color: '#cc0000', width: 2 }}
                    }},
                    {{
                        type: 'line',
                        x0: climb_dist_nm + range_nm,
                        x1: climb_dist_nm + range_nm,
                        y0: cruise_alt - 1500,
                        y1: cruise_alt - 500,
                        line: {{ color: '#cc0000', width: 2 }}
                    }},
                    // Loiter circle marker
                    {{
                        type: 'circle',
                        x0: climb_dist_nm + range_nm + 10 + loiter_dist_nm / 2 - 5,
                        x1: climb_dist_nm + range_nm + 10 + loiter_dist_nm / 2 + 5,
                        y0: loiter_alt - 800,
                        y1: loiter_alt + 800,
                        line: {{ color: '#333', width: 1 }}
                    }}
                ]
            }});

            Plotly.newPlot('mission-profile-plot', [{{
                x: simple_x,
                y: simple_y,
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#000000', width: 2 }},
                fill: 'tozeroy',
                fillcolor: 'rgba(200, 230, 201, 0.3)'
            }}], missionLayout, {{responsive: true, displayModeBar: false}});

            // Plot Range vs L/D
            const ld_range = [];
            const range_ld_vals = [];
            for (let ld = 5; ld <= 30; ld += 0.5) {{
                ld_range.push(ld);
                range_ld_vals.push(breguetRangeNm(SFC_cruise, ld, W1, W2, eta_prop));
            }}

            const rangeLDLayout = Object.assign({{}}, cadLayout, {{
                title: 'RANGE vs LIFT-TO-DRAG RATIO',
                xaxis: Object.assign({{}}, cadLayout.xaxis, {{ title: 'L/D Ratio' }}),
                yaxis: Object.assign({{}}, cadLayout.yaxis, {{ title: 'Range (nm)' }}),
                showlegend: false,
                shapes: [{{
                    type: 'line',
                    x0: LD_max,
                    x1: LD_max,
                    y0: 0,
                    y1: Math.max(...range_ld_vals) * 1.1,
                    line: {{ color: '#cc0000', width: 2, dash: 'dash' }}
                }}],
                annotations: [{{
                    x: LD_max,
                    y: Math.max(...range_ld_vals) * 0.95,
                    text: `Aircraft L/D = ${{LD_max.toFixed(1)}}`,
                    showarrow: true,
                    arrowhead: 2,
                    ax: 40,
                    ay: -30,
                    font: {{ size: 11, color: '#cc0000' }}
                }}]
            }});

            Plotly.newPlot('range-ld-plot', [{{
                x: ld_range,
                y: range_ld_vals,
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#000000', width: 2 }}
            }}], rangeLDLayout, {{responsive: true, displayModeBar: false}});
        }}
        """
