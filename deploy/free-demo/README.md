# Free hosting preparation — Indic AAC Studio

This folder contains a deployable recorded-audio demo of the current AAC interface. `dist/` includes 80 WAVs, 20 each for English, Hindi, Gujarati and Marathi, plus local React/CSS/JS assets. `Indic_AAC_Free_Static_Demo.zip` has index.html at its root and is suitable for static-host uploads. This is not the 3.6 GB model bundle.

The static demo plays included recordings and stores its personal lists in the visitor browser. It cannot execute PyTorch, generate arbitrary new neural speech, clone uploaded voices or authenticate real Google/local backend accounts. These limitations are displayed on the site.

## Cloudflare Pages — recorded demo
1. Sign in to Cloudflare and open Workers & Pages.
2. Create a Pages project using Direct Upload.
3. Upload `Indic_AAC_Free_Static_Demo.zip` (or the dist folder) and deploy.
4. Use the pages.dev URL returned by Cloudflare. No custom domain is needed.

Official upload instructions: https://developers.cloudflare.com/pages/get-started/direct-upload/ . Free-plan limits: https://developers.cloudflare.com/pages/platform/limits/ . All included assets are below the 25 MiB per-file limit.

## GitHub Pages — recorded demo
1. With write access to speechforge/AAC_System, add deploy/free-demo/dist and copy github-pages.yml to .github/workflows/aac-demo.yml.
2. In the repository Settings → Pages, select GitHub Actions as the source.
3. Run the Deploy AAC recorded demo workflow. Use the URL returned by its successful deployment; a URL is not live merely because the repository exists.

GitHub Pages is free for public repositories: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits . The connected GitHub account currently has read-only access to speechforge/AAC_System, so no push or deployment was performed.

## Full AI demonstration
GitHub Pages and static Pages hosting do not run the Python/PyTorch speech backend. The saved WAV demo does not substitute for live voice cloning.

Hugging Face currently offers up to two free ZeroGPU Spaces to eligible personal accounts with verified email and age over 30 days. ZeroGPU is Gradio-only and has per-user daily GPU quotas; the current FastAPI app needs an inference integration/adaptation. See https://huggingface.co/docs/hub/spaces-zerogpu . New ordinary Docker/Gradio compute Spaces require a paid plan even though CPU Basic compute has no hourly cost: https://huggingface.co/docs/hub/spaces-overview . Do not select a paid plan or hardware unless you intend to pay.

This deployment uses Cloudflare Pages Direct Upload only. No tunnel is used.
