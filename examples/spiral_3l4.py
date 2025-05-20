#!/usr/bin/env python3
import sys
import numpy as np
from scipy.constants import c, pi
import openems

mm = 1e-3
GHz = 1e9

# Simulation parameters
fc = 1.3 * GHz
spiral_turns = 2.5  # Number of spiral turns (approximate, will be adjusted for length)
trace_width = 0.25 * mm
spacing = 0.25 * mm
substrate_thickness = 0.5 * mm
foil_thickness = 0.035 * mm
box_size = 10 * mm

# Calculate wavelength and spiral length
lam = c / fc
spiral_length = 0.75 * lam
print(f"λ = {lam*1e3:.2f} mm, 3λ/4 = {spiral_length*1e3:.2f} mm")

# Substrate and metal
em = openems.OpenEMS('spiral_3l4', EndCriteria=1e-5, fmin=0, fmax=3*fc, fsteps=801)
copper = openems.Metal(em, 'copper')
sub = openems.Dielectric(em, 'substrate', eps_r=3.2)

# Z stack
z0 = 0
z1 = substrate_thickness
z2 = z1 + foil_thickness

# Mesh
em.resolution = 0.05 * mm
em.mesh.AddLine('z', z2 + 1*mm)

# Substrate box
start = np.array([-0.5*box_size, 0.5*box_size, z0])
stop  = np.array([0.5*box_size, -0.5*box_size, z1])
sub.AddBox(start, stop, priority=2)

# Generate spiral points (Archimedean spiral)
center_points = []
r0 = 1.5 * mm
spacing_eff = trace_width + spacing
length = 0
phi = 0
phi_step = pi/90
while length < spiral_length:
    r = r0 + spacing_eff * phi / (2*pi)
    x = r * np.cos(phi)
    y = r * np.sin(phi)
    if center_points:
        dx = x - center_points[-1][0]
        dy = y - center_points[-1][1]
        length += np.sqrt(dx*dx + dy*dy)
    center_points.append([x, y])
    phi += phi_step
center_points = np.array(center_points)

# Generate outer and inner edge points for the spiral trace
outer_points = []
inner_points = []
for i, (x, y) in enumerate(center_points):
    r = np.sqrt(x**2 + y**2)
    angle = np.arctan2(y, x)
    # Outward normal for outer edge
    x_out = (r + 0.5*trace_width) * np.cos(angle)
    y_out = (r + 0.5*trace_width) * np.sin(angle)
    # Inward normal for inner edge
    x_in = (r - 0.5*trace_width) * np.cos(angle)
    y_in = (r - 0.5*trace_width) * np.sin(angle)
    outer_points.append([x_out, y_out])
    inner_points.append([x_in, y_in])
# Create closed polygon: outer edge, then reversed inner edge
polygon_points = np.vstack([outer_points, inner_points[::-1]])

# Draw spiral trace as a closed polygon
openems.Polygon(copper,
    priority=9,
    points=polygon_points,
    elevation=[z1, z2],
    normal_direction='z',
    pcb_layer='F.Cu'
)

# Ports at spiral terminals (use centerline for port positions)
port_length = 0.5 * mm
# Outer terminal
start = [center_points[0][0] - port_length, center_points[0][1] + trace_width/2, z1]
stop  = [center_points[0][0], center_points[0][1] - trace_width/2, z2]
openems.Port(em, start, stop, direction='x', z=50)
# Inner terminal
start = [center_points[-1][0], center_points[-1][1] + trace_width/2, z1]
stop  = [center_points[-1][0] + port_length, center_points[-1][1] - trace_width/2, z2]
openems.Port(em, start, stop, direction='x', z=50)

# Write KiCad footprint
em.write_kicad(em.name)

# Run simulation
command = 'view solve'
if len(sys.argv) > 1:
    command = sys.argv[1]
print(command)
em.run_openems(command)
