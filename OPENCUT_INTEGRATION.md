# OpenCut integration

The factory now contains an optional OpenCut CLI adapter.

**Important:** OpenCut-app/OpenCut (the CapCut alternative) currently documents
Editor API/headless rendering as upcoming work, so this project does not invent
an unsupported API. For today's automation, the adapter targets the
code-driven OpenCut distribution that exposes `npx opencut-render <project>`.

Flow:

AI script/assets -> timeline/template -> validate -> OpenCut CLI -> MP4 -> QA

Install Node.js 20+ and create an OpenCut project:

```bash
npx opencut-init factory-template
npx opencut-validate src/examples/factory-template/timeline.ts
```

Configure:

```text
VIDEO_RENDERER=opencut
OPENCUT_PROJECT=factory-template
```

The adapter runs `npx opencut-render factory-template` and copies the generated
MP4 into the factory output.

For the production factory, FFmpeg remains the safe default/fallback. Make.com
should submit jobs to the API and receive a job/webhook result; it should not do
the heavy rendering itself. GitHub Actions should test/build and run smoke
renders, while the dedicated computer/worker performs batch rendering.

When OpenCut-app's stable headless API/SDK is released, this adapter can be
replaced with a native API adapter without changing the upstream job pipeline.
