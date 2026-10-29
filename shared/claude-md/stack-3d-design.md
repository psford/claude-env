# Stack: 3D-Printed Parts (Blender)

<!-- Canonical source: claude-env/shared/claude-md/stack-3d-design.md. -->
<!-- Opt-in for any repo that designs physical parts. Why: docs/decisions.md, 2026-10-28. -->

## Tools
- **FOSS first**, for every tool in the chain: modeling, conversion, slicing.
- **Blender is the default modeler.** Before reaching for anything else, ask: *"Do we need to do something Blender can't do?"* If not, use Blender. If so, name the missing capability, use a FOSS tool for that one step only, and record why in the part's `spec.md`. (Known gap: Blender can't read STEP files, so FreeCAD converts vendor STEP files for fit checks.)
- **Drive Blender through the official Blender Lab MCP server** (`blender-mcp`, add-on `mcp`). Never use MCP servers or add-ons that generate or download models.
- The WSL Blender matches Patrick's Windows Blender minor version (5.2 LTS), so every `.blend` opens on both. `infrastructure/wsl/install-blender.sh` installs and pins it.

## Never Fake It
- **Every printable file (STL/3MF) is exported by Blender** from a named object in a committed `.blend`. Never write mesh files by hand or from code outside Blender. Never print a downloaded or AI-generated model as our part.
- **Build with Blender's own tools:** primitives at exact dimensions, modifiers, booleans, bevels, Geometry Nodes, curves. Never push computed vertex lists into a mesh.
- **The build script is the source of truth.** `cad/<part>/build_<part>.py` runs inside Blender and rebuilds the `.blend` from scratch. GUI tweaks are for exploring; fold them into the script before exporting.
- **The `.blend` is a real, editable model:** millimetres, named objects, live (unapplied) modifiers, and key dimensions as named parameters.
- **Vendor models are for fit checks only,** kept in a `reference` collection and never exported.

## Dimensions and Fits
- Every critical dimension goes in `cad/<part>/spec.md` with its source: a datasheet URL and revision, or a caliper reading and date. Datasheet first, then confirm with calipers; calipers win. Design for the exact part number bought.
- **Don't spend prints tuning press fits.** Low-load hardware (nuts, threaded inserts, magnets) goes in a light slip-fit pocket (~0.1–0.2 mm clearance per side) with a dab of CA glue. Use heat-set inserts only for joints that carry real load or get taken apart often.
- Outdoor parts are ASA (or PETG), never PLA.

## Before Anything Is Printed
1. Check every `spec.md` dimension in Blender and report pass/fail.
2. Run printability checks: watertight, no self-intersections, wall thickness, overhangs.
3. Show Patrick renders, plus the `.blend` path to open on Windows (`\\wsl.localhost\Ubuntu-24.04\home\patrick\...`).
4. Print a fit-test coupon for any feature that must fit precisely.
5. After printing, record the measurements in `spec.md` and fold fixes back into the build script.

## Running Blender in WSL
- **Start it with `blender &`.** The window opens on Patrick's desktop through WSLg, and the MCP add-on auto-starts on `localhost:9876`. MCP tools need that instance running; the `*_for_cli` tools spawn their own background Blender instead.
- **The MCP server is registered with Claude Code at user scope** (`claude mcp add --scope user blender -- blender-mcp`; the installer does this), so it loads in any session, whatever folder it starts in. Don't add it to a repo's `.mcp.json`. A new registration only appears after a session restart.
- **It runs on Patrick's RTX 4090.** `~/.local/bin/blender` is a launcher that sets up Mesa's OpenGL-on-DirectX-12 driver, pinned to the NVIDIA adapter, with Blender on X11. Always launch through it, never the binary under `~/.local/opt`. That gets OpenGL, which would otherwise land on software rendering or a broken Wayland window. Check with `gpu.platform.renderer_get()`, which should read `D3D12 (NVIDIA GeForce RTX 4090)`.
- **Window and area screenshots come back black** on this driver path; only the readback is affected, the window itself draws correctly. To look at a part, render instead: the MCP `render_viewport_to_path` / `render_thumbnail_to_path` tools, or `bpy.ops.render.opengl` for the viewport with its overlays.
- **The MCP server runs Claude-written code inside Blender with no guards.** Inside the WSL cage, that's the same privilege as Bash. Never point it at a Blender running on Windows: that would be an escape from the cage.
