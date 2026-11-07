# Stack: Physical Parts (Blender, build123d, FreeCAD)

<!-- Canonical source: claude-env/shared/claude-md/stack-3d-design.md. -->
<!-- Opt-in for any repo that designs physical parts. Why: docs/decisions.md, 2026-10-28. -->

## Tools
- **FOSS first**, for every tool in the chain: modeling, conversion, slicing.
- **Blender is the default modeler.** Before reaching for anything else, ask: *"Do we need to do something Blender can't do?"* If not, use Blender. If so, name the missing capability, use a FOSS tool for that one step only, and record why in the part's `spec.md`. (Known gap: Blender can neither read nor write STEP files. FreeCAD or build123d converts vendor STEP files for fit checks.)
- **Drive Blender through the official Blender Lab MCP server** (`blender-mcp`, add-on `mcp`). Never use MCP servers or add-ons that generate or download models.
- The WSL Blender matches Patrick's Windows Blender minor version (5.2 LTS), so every `.blend` opens on both. `infrastructure/wsl/install-blender.sh` installs and pins it.
- **Parts headed for injection molding are the exception to Blender as modeler: build them in build123d, with STEP as model of record.** A toolmaker needs exact surfaces with real draft, and Blender can't write them. Blender stays the review environment.
- **FreeCAD is the second reader for STEP files.** Open every model-of-record STEP file in it and compare faces, volume and size with the build. `infrastructure/wsl/install-freecad.sh` installs it.

## Never Fake It
- **Every printable file (STL/3MF) is exported by Blender** from a named object in a committed `.blend`. Never write mesh files by hand or from code outside Blender. Never print a downloaded or AI-generated model as our part.
- **Build with Blender's own tools:** primitives at exact dimensions, modifiers, booleans, bevels, Geometry Nodes, curves. Never push computed vertex lists into a mesh.
- **The build script is the source of truth.** `cad/<part>/build_<part>.py` runs inside Blender and rebuilds the `.blend` from scratch. GUI tweaks are for exploring; fold them into the script before exporting.
- **The `.blend` is a real, editable model:** millimetres, named objects, live (unapplied) modifiers, and key dimensions as named parameters.
- **Vendor models are for fit checks only,** kept in a `reference` collection and never exported.

## Multi-Part Models
Renders aren't the whole deliverable. Patrick pokes around in Blender, so anything with more than one part comes with renders and a `.blend` holding both of these, built by the build script, without being asked. Open it in Blender for him.
- **A tidy Scene Collection, assembled.** Each component is one click to turn off: `enclosure` for the parts we make, `reference` for everything else, with a run of small parts (screws) as one collection. Everything the parts are built from goes in a `construction` collection excluded from the view layer.
- **An exploded view,** keyframed on the timeline with `assembled` and `exploded` markers, frame 1 assembled. Parent each part's Boolean operands to it, or its cuts stay behind when it moves. Save the file on frame 1, and have checks and renders go to frame 1 first: an STL exported on another frame comes out shifted.

## Injection-Molded Parts
Design for the mold from the start: draft, even walls, moldable latches, and a material choice. Prototype the design that will be molded.
- **Pull the STEP files back into Blender as a conversion.** Read the file back, mesh that, and import the mesh, so the review shows the real file. The STEP files stay the model of record, and printable STLs are exported by Blender from those meshes.
- **Check draft and undercuts on the exact STEP files, not a mesh.** At 1 degree a ray running along a faceted surface clips the next facet, so mesh checks report false undercuts and miss real ones.
- **Sweep each part along its assembly path.** A check of parts in their final positions passes parts that can't actually be put together.

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

## Running FreeCAD in WSL
- **`freecad`** opens the GUI on the RTX 4090, through the same d3d12 setup as Blender. `freecad freecadcmd <script>` runs a script with no window. Window screenshots work here, unlike Blender's.
- **The MCP bridge is registered with Claude Code at user scope as `freecad`, but it only works if the bridge is already running when a session starts.** The server connects as it starts and exits if nothing answers. Start it in FreeCAD first: the Robust MCP Bridge workbench, then Start Bridge. Auto-start is off, and stays off unless Patrick asks.
- **Ports:** XML-RPC on 9875, socket on 9877, because Blender's add-on holds 9876.
- **`FREECAD_ALLOW_UNSAFE_CODE` stays off unless Patrick turns it on.** That keeps `execute_python` and the macro tools out of the tool list, though the setting isn't a sandbox: a paired client can still send code directly. Drawings and FEM have no dedicated tools and would need it.
- **It's community code that can run Python as Patrick.** Install only the commits pinned in `install-freecad.sh`, and review a new version's source before bumping them. Never point it at a FreeCAD running on Windows. Its parts-library tool only reads a local folder, and stays unused.
- **Never overwrite FreeCAD's preferences while it's running:** it writes them back when it closes. `user.cfg` is the file to leave alone.
