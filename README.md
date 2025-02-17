# Screenplay Dreamer

Turn your photos into cinematic screenplays using AI. This app uses Google's Gemini 2.0
model to analyze images and create compelling screenplay scenes with proper
formatting and structure. Upload any photo and watch as it transforms into a
professionally formatted screenplay scene.

This is not an official Google product and I'm also unlikely to maintain it
because the Generative AI space is moving very fast. Use this as an example and
I hope you find some value in it. If you do find parts you like or don't like, I
appreciate hearing your comments! Find me on the socials
([www.wietsevenema.eu](https://www.wietsevenema.eu) has links)

## Features

- Image upload and processing
- AI-powered screenplay writing
- Structured output to parse the screenplay
- User authentication with Google Sign In
- Public/unlisted screenplay sharing
- Gallery view of generated screenplays

## Prompting Strategy

The screenplay generation follows a three-stage prompting pipeline:

1. **Scene Analysis**: First, analyze the uploaded image to determine potential
   movie genres, visual themes, and cinematic context.

2. **Screenplay Generation**: Using the analysis and the image, generate the
   screenplay scene. The image is treated as a still from the opening shot,
   allowing the LLM to build a narrative more easily.

3. **Structure Formatting**: Finally, the raw screenplay output is processed
   through a formatting prompt with structured output.

## Prerequisites

- Python 3.12+
- Poetry for dependency management
- A Google Cloud project with billing enabled
- Google Cloud credentials with access to:
  - Gemini API on Vertex
  - Cloud Storage
  - Firestore
  - Cloud Run

## Setup


### Set up Google Cloud:
   - Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
   - Create a new project or select an existing one
   - Configure the project as default:
     `gcloud config set project YOUR_PROJECT_ID`. The project ID is displayed in
     the [Google Cloud web console](https://console.cloud.google.com/) next to
     the project number, and when you click on the project selector at the top
     of the console.
   - Authenticate: `gcloud auth login --update-adc`. The flag `--update-adc` makes sure to update
     the local credentials that are used by the client libraries when accessing Google Cloud APIs.

### Enable services
Enable required Google Cloud APIs:
  - Gemini API: [aiplatform.googleapis.com](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com)
  - Cloud Storage: [storage.googleapis.com](https://console.cloud.google.com/apis/library/storage.googleapis.com)
  - Firestore: [firestore.googleapis.com](https://console.cloud.google.com/apis/library/firestore.googleapis.com)
  - Secret Manager: [secretmanager.googleapis.com](https://console.cloud.google.com/apis/library/secretmanager.googleapis.com)
  - Cloud Build: [cloudbuild.googleapis.com](https://console.cloud.google.com/apis/library/cloudbuild.googleapis.com)
  - Cloud Run: [run.googleapis.com](https://console.cloud.google.com/apis/library/run.googleapis.com)
  - Artifact Registry: [artifactregistry.googleapis.com](https://console.cloud.google.com/apis/library/artifactregistry.googleapis.com)

### Create required resources:
   - Create a Cloud Storage bucket for image storage:
     [console.cloud.google.com/storage](https://console.cloud.google.com/storage)
   - Create the default Firestore database in native mode:
     [console.cloud.google.com/firestore](https://console.cloud.google.com/firestore)

### Configure Sign In with Google
Enable Google Auth Platform to use Sign in with Google:
[console.cloud.google.com/auth/overview](https://console.cloud.google.com/auth/overview)

Configure `http://localhost:8000` as an Authorised JavaScript origin

### Configure Firestore indexes
... instructions pending. For now, just watch the logs when you click around in
the localhost deployment and follow any links it suggests when you get a HTTP
500...

### Run the application on localhost

First, Make sure to have a working local Python development setup with Python
3.12 or newer. Refer to the notes I wrote on
[using pyenv for Python version management and poetry for dependency management](https://wietsevenema.eu/installing-python-on-your-development-workstation/).

Install dependencies
```bash
poetry install
```

Make a copy of `.env.example` to `.env` and fill in any settings.

Start the local server
```bash
poetry run uvicorn main:app --reload
```
Here's what that command does:
- `poetry run`:
Executes a command within the virtual environment managed by Poetry, with all the dependencies you just installed
- `uvicorn`:
Uvicorn is a web server implementation for Python
- `main:app`:
This specifies the application to run. `main` refers to the file named main.py.
`app` refers to the variable in `main.py` that holds the application instance.
- `--reload`:
When this flag is used, Uvicorn automatically restarts the server when it detects local file changes - great for local development.

### Deploy to Cloud Run:
Replace the values with your settings and set the following environment variables:
```bash
export PROJECT_ID="your-project-id"
export BUCKET_NAME="your-bucket-name"
export GOOGLE_CLIENT_ID="your-google-client-id"
```
 * PROJECT_ID: The project ID is what you configured earlier with `gcloud config set project`
 * BUCKET_NAME: The bucket name is the name of the Cloud Storage bucket (*without* `gs://`)
 * GOOGLE_CLIENT_ID: You created a Google OAuth 2.0 Client ID when setting up the Google Auth service Go to the Google Cloud Console and navigate to "APIs & Services" -> "Credentials." 


```bash
gcloud run deploy screenplay-dreamer \
  --source . \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,\
BUCKET_NAME=$BUCKET_NAME,\
GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID" \
  --set-secrets="JWT_SECRET=jwt-secret:latest"\
  --allow-unauthenticated \
  --port 8080
```
Here's what the command does:
* `gcloud run deploy`:
This is the base command for deploying a service to Cloud Run
* `screenplay-dreamer`
The name of the service. If a service with the name doesn't exist, it will be created. If it does exist, it will be updated with the new deployment.
* `--source .`:
This tells Cloud Run to use the source code located in the current directory (.) to build and deploy the application. Because there is a `Dockerfile` in the directory, it'll use that to containerize the application.
* `--allow-unauthenticated`:
Allows anyone on the internet to access the Cloud Run service. This is suitable for public websites or APIs.
* `--port 8080`:
Specifies that the app listens on port `8000` for incoming web requests.

## Project Structure

- `src/`: Core application code
  - `auth/`: Authentication middleware
  - `core/`: Core settings and dependencies
  - `routes/`: API endpoints and request handlers
  - `storage/`: Database and image storage operations
  - `writing/`: Screenplay generation and scene analysis
- `prompts/`: AI prompt templates
  - `system/`: System prompts for AI context
  - `chat/`: Scene analysis and generation prompts
- `static/`: CSS, images, and other static assets
  - `css/`: Stylesheets
- `templates/`: Jinja2 HTML templates

## License

Apache License 2.0 (see LICENSE)
