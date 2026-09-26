from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image
from mcp.types import ToolAnnotations, TextContent, ImageContent
from pydantic import BaseModel, Field

from .runtime import Runtime


class FaceChange(BaseModel):
    id: str
    value: float = Field(strict=True, allow_inf_nan=False)


class ParameterChange(BaseModel):
    id: str
    value: bool | float | str | list[float] | list[list[float]]


def create_server(lab: Path, variant: str, model_file: Path | None = None) -> FastMCP:
    runtime = Runtime(lab)
    initialized = False
    operation_lock = asyncio.Lock()

    async def initialize_runtime():
        nonlocal runtime, initialized
        if initialized:
            return
        try:
            await asyncio.to_thread(runtime.start)
            await runtime.initialize(variant, model_file)
            initialized = True
        except BaseException:
            await asyncio.to_thread(runtime.close)
            runtime = Runtime(lab)
            raise

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield runtime
        finally:
            await asyncio.to_thread(runtime.close)

    mcp = FastMCP('VRoid Character MCP', lifespan=lifespan,
        instructions='Controls a disposable VRoid Studio copy through native methods. '
        'Call list_face_params first and use its model_token as expected_model. '
        'Use list_parameters for colors, expressions, general, accessories and hair. '
        'Use list_hair_nodes(category) then its node id as scope for hair parameters. '
        'Use list_accessories then instance id as scope for accessory parameters. '
        'Parameter types include float, int, bool, enum index, RGBA color, vector3, quaternion and curve control points. '
        'Use set_height for a measured centimeter target. '
        'Use capture_review before and after edits for native multi-view images and parameter comparisons; inspect the images before judging appearance. '
        'List the relevant parameters or presets before applying them. Relist clothing parameters after changing clothes. '
        'No desktop input, texture painting, strand drawing, custom material authoring, or VRM export. '
        'A batch follows VRoid native history and can require multiple undo steps.')
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    edit = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    def ready_tool(**options):
        """Publish the catalog immediately; start Unity only on the first tool call."""
        def register(function):
            @wraps(function)
            async def ready(*args, **kwargs):
                async with operation_lock:
                    await initialize_runtime()
                    return await function(*args, **kwargs)
            return mcp.tool(**options)(ready)
        return register

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
    async def restart_session(discard_unsaved: bool = False) -> dict:
        """Recreate only this MCP-owned VRoid copy, discarding its unsaved changes.

        Requires explicit discard_unsaved=true. Save first when possible; do not use
        this to silently discard a user's work. A new model_token invalidates old IDs.
        Works after COPY_DISCONNECTED or an uncertain native call. Never touches other VRoid processes.
        """
        nonlocal runtime, initialized
        if not discard_unsaved:
            raise ValueError('Explicit discard_unsaved=true required; this discards the MCP copy unsaved changes')
        async with operation_lock:
            await asyncio.to_thread(runtime.close)
            runtime = Runtime(lab)
            initialized = False
            await initialize_runtime()
            return await runtime.status()

    @ready_tool(annotations=read)
    async def get_status() -> dict:
        """Check the copy, current model, background processing, and model update state."""
        return await runtime.status()

    @ready_tool(annotations=read)
    async def list_parameters(domain:Literal['face','body','clothing','colors','expressions','general','hair','hair_bones','accessories','photo'],
                              scope:str|None=None,category:str|None=None,offset:int=Field(default=0,ge=0),limit:int=Field(default=200,ge=1,le=500))->dict:
        """List typed native controls with values, units/ranges/options. Hair requires category + node scope.

        Accessories require instance scope. Expressions optionally use an expression ID as scope.
        Colors use RGBA 0..1. Read every next_offset page when discovering controls.
        General covers outline, rim light, shading, gaze limits and spring amplitude.
        """
        return await runtime.parameter_call('list_parameters',{'domain':domain,'scope':scope,'category':category,'offset':offset,'limit':limit})

    @ready_tool(annotations=edit)
    async def set_parameters(expected_model:str,domain:Literal['face','body','clothing','colors','expressions','general','hair','hair_bones','accessories','photo'],
                             changes:list[ParameterChange],scope:str|None=None,category:str|None=None)->dict:
        """Set 1-64 typed parameters from a fresh list_parameters result; all values validate before writes.

        Hair requires category and node scope. Accessories require instance scope. Native history supports Undo.
        Curves are arrays of [x,y] control points, quaternions [x,y,z,w], vectors [x,y,z], colors [r,g,b,a].
        A native error can leave a partial batch: inspect ok/applied/error. Preset or structure changes require relisting.
        """
        return await runtime.parameter_call('set_parameters',{'expected_model':expected_model,'domain':domain,
            'changes':[c.model_dump() for c in changes],'scope':scope,'category':category},True)

    @ready_tool(annotations=read)
    async def list_presets(area:Literal['face','body','hair','clothing'],category:str|None=None,offset:int=Field(default=0,ge=0),limit:int=Field(default=100,ge=1,le=200))->dict:
        """List owned preset options across every face/body/hair/clothing category."""
        return await runtime.list_presets(area,category,offset,limit)

    @ready_tool(annotations=edit)
    async def apply_preset(expected_model:str,area:Literal['face','body','hair','clothing'],preset_id:str)->dict:
        """Apply an owned native preset from list_presets. Relist parameters after structural changes."""
        return await runtime.apply_preset(area,expected_model,preset_id)

    @ready_tool(annotations=read)
    async def list_hair_nodes(category:str='HairFront')->dict:
        """List groups and strands in HairFront, HairBack, AllHair, HairTied, HairSideburns, HairAhoge or HairHanege.

        Use a returned id as scope with list_parameters(domain='hair',category=...).
        """
        return await runtime.parameter_call('list_hair_nodes',{'category':category})

    @ready_tool(annotations=read)
    async def list_hair_bone_groups(category:str='HairFront')->dict:
        """List hair physics groups. list_parameters(domain='hair_bones',category=...) exposes bone count, root rate, stiffness, gravity and radius."""
        return await runtime.parameter_call('list_hair_bone_groups',{'category':category})

    @ready_tool(annotations=edit)
    async def generate_hair_bones(expected_model:str,category:str='HairFront')->dict:
        """Generate native hair bone groups using hair_bones/generation parameters. Existing grouping can be replaced; native Undo supported."""
        return await runtime.parameter_call('generate_hair_bones',{'expected_model':expected_model,'category':category},True)

    @ready_tool(annotations=edit)
    async def edit_hair_structure(expected_model:str,category:str,action:Literal['add_procedural','remove'],node_id:str|None=None)->dict:
        """Create a procedural hair group or remove a group/strand. Native Undo supported. No manual strand drawing."""
        return await runtime.parameter_call('edit_hair_structure',{'expected_model':expected_model,'category':category,'action':action,'node_id':node_id},True)

    @ready_tool(annotations=read)
    async def list_accessory_templates()->dict:
        """List accessory templates across glasses, animal ears, tails and hats."""
        return await runtime.parameter_call('list_accessory_templates')

    @ready_tool(annotations=read)
    async def list_accessories()->dict:
        """List worn accessory instance IDs. Use an id as scope for accessory parameters."""
        return await runtime.parameter_call('list_accessories')

    @ready_tool(annotations=edit)
    async def edit_accessories(expected_model:str,action:Literal['add','remove','duplicate'],template_id:str|None=None,instance_id:str|None=None)->dict:
        """Add a template, remove or duplicate a worn accessory. Relist instances and parameters afterwards."""
        return await runtime.parameter_call('edit_accessories',{'expected_model':expected_model,'action':action,'template_id':template_id,'instance_id':instance_id},True)

    @ready_tool(annotations=read)
    async def list_expressions()->dict:
        """List expression IDs. Definition weights are under list_parameters(domain='expressions',scope=id)."""
        return await runtime.parameter_call('list_expressions')

    @ready_tool(annotations=edit)
    async def set_preview_mode(expected_model:str,mode:Literal['photo','edit'])->dict:
        """Enter native photo preview or return to model editing. Photo parameters are session-only, not saved in .vroid.

        Use list_parameters(domain='photo') for poses, hand poses, lighting, wind, effects and gaze.
        Return to edit before editing/saving the character. No mouse/keyboard automation.
        """
        return await runtime.parameter_call('set_preview_mode',{'expected_model':expected_model,'mode':mode},True)

    @ready_tool(annotations=edit)
    async def set_photo_camera(expected_model:str,position:list[float],target:list[float])->dict:
        """Set photo camera position and look-at target as [x,y,z] meters, then screenshot(view='photo')."""
        return await runtime.parameter_call('set_photo_camera',{'expected_model':expected_model,'position':position,'target':target},True)

    @ready_tool(annotations=edit)
    async def preview_expression(expected_model:str,expression:str|None=None)->dict:
        """Preview an expression by ID; null resets the visual preview. This does not change expression weights."""
        return await runtime.parameter_call('preview_expression',{'expected_model':expected_model,'expression':expression},True)

    @ready_tool(annotations=read)
    async def get_height()->dict:
        """Read native VRoid height in centimeters, label and current live measurement."""
        return await runtime.parameter_call('get_height')

    @ready_tool(annotations=edit)
    async def set_height(expected_model:str,centimeters:float=Field(ge=20,le=400,allow_inf_nan=False),tolerance_cm:float=Field(default=.05,ge=.01,le=.5))->dict:
        """Adjust whole-body size and verify native measured height within tolerance. Preserves relative proportions.

        Native reachable range varies by model. Non-convergence restores the initial scale; native errors
        require inspecting current state. Solver steps use native history.
        Hair and other proportions may affect VRoid's measured height, so call this after styling the model.
        """
        return await runtime.set_height(expected_model,centimeters,tolerance_cm)

    @ready_tool(annotations=read)
    async def list_face_params() -> dict:
        """List UI face sliders, localized labels, ranges, current values, aliases and model_token."""
        return await runtime.list_face_params()

    @ready_tool(annotations=edit)
    async def set_face_params(expected_model: str, changes: list[FaceChange]) -> dict:
        """Set 1-64 face sliders. All values are validated first; duplicate aliases are rejected.

        Only the model matching expected_model may change. Native execution failures can
        produce a partial result; inspect applied and error before doing further work.
        """
        return await runtime.set_face_params(expected_model,[item.model_dump() for item in changes])

    @ready_tool(annotations=read)
    async def list_body_params() -> dict:
        """List body proportions, height and limb sliders, ranges, values and model_token."""
        return await runtime.list_params('body')

    @ready_tool(annotations=edit)
    async def set_body_params(expected_model: str, changes: list[FaceChange]) -> dict:
        """Set 1-64 body parameters from list_body_params through native VRoid history."""
        return await runtime.set_params('body',expected_model,[item.model_dump() for item in changes])

    @ready_tool(annotations=read)
    async def list_clothing_params() -> dict:
        """List shape sliders on currently worn clothes. IDs change when garments change."""
        return await runtime.list_params('clothing')

    @ready_tool(annotations=edit)
    async def set_clothing_params(expected_model: str, changes: list[FaceChange]) -> dict:
        """Set garment shape sliders from a fresh list_clothing_params result."""
        return await runtime.set_params('clothing',expected_model,[item.model_dump() for item in changes])

    @ready_tool(annotations=read)
    async def list_hair_presets(category: str|None=None, offset: int=Field(default=0,ge=0),limit:int=Field(default=100,ge=1,le=200)) -> dict:
        """List owned built-in hairstyles and parts, category IDs and pagination. Labels are category/resource codes."""
        return await runtime.list_presets('hair',category,offset,limit)

    @ready_tool(annotations=edit)
    async def apply_hair_preset(expected_model: str,preset_id: str) -> dict:
        """Apply an owned hairstyle or hair part from list_hair_presets; native history supports Undo."""
        return await runtime.apply_preset('hair',expected_model,preset_id)

    @ready_tool(annotations=read)
    async def list_clothing_presets(category: str|None=None, offset: int=Field(default=0,ge=0),limit:int=Field(default=100,ge=1,le=200)) -> dict:
        """List owned built-in outfits, tops, bottoms, shoes and other clothing categories."""
        return await runtime.list_presets('clothing',category,offset,limit)

    @ready_tool(annotations=edit)
    async def apply_clothing_preset(expected_model: str,preset_id: str) -> dict:
        """Apply a clothing preset. It can replace conflicting garments; relist clothing sliders afterwards."""
        return await runtime.apply_preset('clothing',expected_model,preset_id)

    @ready_tool(annotations=edit)
    async def undo(expected_model: str, steps: int = Field(default=1,ge=1,le=32)) -> dict:
        """Undo native history for any area. Returns face parameters; relist other areas to inspect them."""
        return await runtime.history('undo',expected_model,steps)

    @ready_tool(annotations=edit)
    async def redo(expected_model: str, steps: int = Field(default=1,ge=1,le=32)) -> dict:
        """Redo native history for any area. Returns face parameters; relist other areas to inspect them."""
        return await runtime.history('redo',expected_model,steps)

    @ready_tool(annotations=read)
    async def screenshot(expected_model: str, view: str = 'front', size: int = Field(default=512,ge=256,le=2048)) -> Image:
        """Return native PNG, size 256..2048: front/side/back/three_quarter for head; full_ prefix for body; photo for posed preview."""
        return Image(data=await runtime.screenshot(view,expected_model,size),format='png')

    @ready_tool(annotations=ToolAnnotations(readOnlyHint=False,destructiveHint=False,openWorldHint=False))
    async def capture_review(expected_model: str, label: str = Field(default='',max_length=80),
                             views: list[str] | None = None, size: int = Field(default=1024,ge=256,le=2048),
                             baseline_id: str | None = None) -> list[TextContent | ImageContent]:
        """Capture 1-6 native model views for AI visual inspection and save PNGs + numeric state under lab/reviews.

        Defaults: front, three_quarter, full_front, full_back. Requires edit mode. Returns images directly,
        paths, model height, capture_id and a visual checklist; no OCR, clicks, automated beauty scoring,
        or automatic collision verdict. Pass baseline_id from an earlier review with identical views/size
        to get before/after images and face/body/clothing/color parameter differences. Hair geometry
        changes must be inspected visually. Different model tokens are reported explicitly.
        Does not edit or save the character; it writes only review artifacts and hides editor guides.
        """
        selected=views if views is not None else ['front','three_quarter','full_front','full_back']
        manifest,images=await runtime.capture_review(expected_model,selected,size,label,baseline_id)
        summary={k:v for k,v in manifest.items() if k!='state'}
        summary['height']=manifest['state']['height']
        content=[TextContent(type='text',text=json.dumps(summary,ensure_ascii=False))]
        for caption,data in images:
            content.append(TextContent(type='text',text=caption))
            content.append(Image(data=data,format='png').to_image_content())
        return content

    @ready_tool(annotations=edit)
    async def save_as(expected_model: str, filename: str) -> dict:
        """Save a new .vroid file under the lab's saves/ folder. Existing files are never overwritten."""
        return await runtime.save_as(filename,expected_model)

    return mcp


def main() -> None:
    parser=argparse.ArgumentParser(description='Local VRoid character MCP; always launches a designated copy.')
    parser.add_argument('--lab',required=True,type=Path,help='Directory containing a physical app/VRoidStudio.exe copy')
    parser.add_argument('--variant',choices=['F00','M00'],default='F00')
    parser.add_argument('--model',type=Path,help='Optional .vroid already inside the lab; otherwise creates a new model')
    args=parser.parse_args()
    create_server(args.lab,args.variant,args.model).run(transport='stdio')


if __name__=='__main__':main()
