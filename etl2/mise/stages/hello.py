from __future__ import annotations
from pathlib import Path
from ..dag import Stage, Context
from ..io import write_json
import time

def HelloStage(cfg):
    out_file = cfg.build_root / "out" / "hello.json"
    def _run(ctx: Context):
        # pretend to do work
        time.sleep(0.05)
        write_json(out_file, {"message": "mise says hello", "built_at": int(time.time())})
    return Stage(
        id="HELLO",
        name="Hello, mise",
        inputs=[],              # no inputs
        outputs=[out_file],     # declare output
        run=_run,
    )
