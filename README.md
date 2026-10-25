# LogScience Lab website

Land-Ocean-Groundwater Science group at HKUST(GZ). Current version: **2.0**, confirmed on 2026-10-26 and recorded by Git tag **v2.0**. See [the changelog](CHANGELOG.md). Production website deployment is managed separately.

## Local preview

Use the active repository under E:/HKUSTgz/GroupWebCoding/03_website/LogScience.github.io.
With Docker Desktop running and the existing image available:

```powershell
docker compose up -d --no-build
```

Open http://localhost:4000/. After source changes on this Windows mount:

```powershell
docker compose restart jekyll-site
docker compose logs --tail 20 jekyll-site
```

Wait for the build to complete. A new environment can build the image with docker compose up -d --build.

## Maintenance

Read [the Chinese content guide](CONTENT_GUIDE.zh-CN.md) for JSON fields, image delivery, input templates and checks. Edit sources, never _site. Workspace context and provenance live outside this repository in 01_project_context and 02_content_materials.

Six core pages use _layouts/lab.html, assets/css/lab.css and minimal local JavaScript. Original images and legacy source pages remain recoverable. Research/Team/Publications share stable IDs. News links to original articles; current recruitment is separate and appears on Contact.

## Publishing

The student preview is https://xiaoma2000.github.io/LogScience.github.io/ once the Pages workflow succeeds. See [publishing and PI handoff](PUBLISHING.zh-CN.md). The workflow derives its address from Pages metadata, while local preview and the v2.0 tag remain unchanged.

Iterate locally. Push only after the user and PI agree a draft and the user explicitly requests upload. Student: xiaoma2000/LogScience.github.io. Independent production: YiLouisLIU/YiLouisLIU.github.io. Forks do not update production automatically. Verify url/baseurl and Pages deployment when handing over.

## Attribution

Started with [Academic Pages](https://github.com/academicpages/academicpages.github.io), based on Minimal Mistakes. Existing license and attribution notices are retained. The six-page lab design and content-maintenance tools are local project additions.
