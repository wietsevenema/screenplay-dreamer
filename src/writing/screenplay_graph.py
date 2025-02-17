from typing import TypedDict, Optional, List, Union
from src.core.settings import settings
import re
from langgraph.graph import Graph
from google import genai
from google.genai import types
from src.writing.template_loader import TemplateLoader
from pydantic import BaseModel


class ScreenplayGenerator:
    """Handles generation of screenplays from images using a workflow graph."""

    MIME_TYPE = "image/jpeg"

    def __init__(self, client: genai.Client):
        """Initialize with a Gemini AI client."""
        self.client = client
        self.prompt_templates = TemplateLoader()

    def _generate_scene(self, state: "SceneState") -> "SceneState":
        """Generate a screenplay scene directly from the image"""
        # Track which model was used
        state["models"].add(settings.CREATIVE_MODEL)

        scene_prompt = self.prompt_templates.get_template(
            "chat/screenplay_scene.txt",
            genre=state.get("genre"),
            analysis=state.get("analysis", ""),
        )
        system_prompt = self.prompt_templates.get_template("system/screenwriter.txt")

        response = self.client.models.generate_content(
            model=settings.CREATIVE_MODEL,
            contents=[
                types.Part.from_bytes(
                    data=state["image_data"], mime_type=self.MIME_TYPE
                ),
                scene_prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            ),
        )
        state["scene"] = response.text
        return state

    def _analyze_still(self, state: "SceneState") -> "SceneState":
        """Analyze the image to determine likely genre and related movies"""
        # Track which model was used
        state["models"].add(settings.CREATIVE_MODEL)

        analysis_prompt = self.prompt_templates.get_template("chat/analyze_still.txt")

        response = self.client.models.generate_content(
            model=settings.CREATIVE_MODEL,
            contents=[
                types.Part.from_bytes(
                    data=state["image_data"], mime_type=self.MIME_TYPE
                ),
                analysis_prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction="You're a professional screenwriter", temperature=0.7
            ),
        )

        state["analysis"] = response.text
        return state

    def _structure_scene(self, state: "SceneState") -> "SceneState":
        """Convert raw screenplay text into structured format using Gemini"""
        # Track which model was used
        state["models"].add(settings.FLASH_MODEL)

        full_prompt = self.prompt_templates.get_template(
            "chat/structure_scene.txt", screenplay=state["scene"]
        )

        response = self.client.models.generate_content(
            model=settings.FLASH_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=SCREENPLAY_SCHEMA,
            ),
        )

        # Parse the response into our Pydantic model
        scene_data = ScreenplayScene.model_validate_json(response.text)
        state["genre"] = scene_data.genre

        # Clean up manner and sound fields
        for element in scene_data.elements:
            if isinstance(element, DialogueElement) and element.manner:
                # Remove surrounding parentheses
                element.manner = re.sub(r"^\(?(.*?)\)?$", r"\1", element.manner)
                # If manner is now empty or just spaces, set to None
                if not element.manner.strip():
                    element.manner = None
            elif isinstance(element, SoundElement):
                element.sound = re.sub(r"^\(?(.*?)\)?$", r"\1", element.sound)

        # Store the structured scene
        state["structured_scene"] = scene_data

        return state

    async def generate_from_image(
        self,
        image_data,
    ) -> "SceneState":
        """
        Generate a complete screenplay from an image

        Args:
            image_data Raw image bytes

        Returns:
            SceneState containing the generated screenplay and metadata
        """
        # Initialize the graph state
        initial_state: SceneState = {
            "scene": "",
            "models": set(),
            "image_data": image_data,
        }

        # Create and run the workflow
        workflow = Graph()

        # Define nodes with bound methods
        workflow.add_node(
            "analyze_still",
            self._analyze_still,
        )
        workflow.add_node(
            "generate_scene",
            self._generate_scene,
        )
        workflow.add_node("structure_scene", self._structure_scene)

        workflow.add_edge("analyze_still", "generate_scene")
        workflow.add_edge("generate_scene", "structure_scene")

        workflow.set_entry_point("analyze_still")
        workflow.set_finish_point("structure_scene")

        # Run the workflow and return the final state
        runnable = workflow.compile()
        return await runnable.ainvoke(initial_state)


class DialogueElement(BaseModel):
    type: str = "dialogue"
    character: str
    line: str
    manner: Optional[str] = None


class VisualElement(BaseModel):
    type: str = "visual"
    visual: str


class SoundElement(BaseModel):
    type: str = "sound"
    sound: str


class SceneEndingElement(BaseModel):
    type: str = "scene_ending"
    transition: str


class ScreenplayScene(BaseModel):
    genre: str
    scene_heading: str
    elements: List[
        Union[DialogueElement, VisualElement, SoundElement, SceneEndingElement]
    ]


class SceneState(TypedDict):
    genre: Optional[str] = None
    scene: str
    structured_scene: ScreenplayScene
    analysis: Optional[str] = None
    models: set[str] = set()


# Response schema for the structure_scene method
SCREENPLAY_SCHEMA = {
    "type": "OBJECT",
    "title": "Screenplay Scene",
    "description": "A structured representation of a screenplay scene",
    "required": ["scene_heading", "genre"],
    "properties": {
        "genre": {"type": "STRING", "description": "The movie genre"},
        "scene_heading": {
            "type": "STRING",
            "description": "Standard screenplay scene heading (e.g., 'INT. COFFEE SHOP - DAY')",
        },
        "elements": {
            "type": "ARRAY",
            "description": "An ordered list of the elements in the script",
            "items": {
                "description": "An item in the script",
                "any_of": [
                    {
                        "title": "Visual",
                        "description": "Describes anything visually perceived by the audience",
                        "type": "OBJECT",
                        "properties": {
                            "type": {
                                "type": "STRING",
                                "description": "Always 'visual'",
                            },
                            "visual": {
                                "type": "STRING",
                                "description": "The description",
                            },
                        },
                        "property_ordering": ["type", "visual"],
                        "required": ["type", "visual"],
                    },
                    {
                        "title": "Sound",
                        "description": "Specifies a sound effect or ambient sound",
                        "type": "OBJECT",
                        "properties": {
                            "type": {
                                "type": "STRING",
                                "description": "Always 'sound'",
                            },
                            "sound": {
                                "type": "STRING",
                                "description": "The sound description (e.g., 'The clatter of cups and saucers').",
                            },
                        },
                        "property_ordering": ["type", "sound"],
                        "required": ["type", "sound"],
                    },
                    {
                        "title": "Scene ending",
                        "description": "The scene ending transition",
                        "type": "OBJECT",
                        "properties": {
                            "type": {
                                "type": "STRING",
                                "description": "Always 'scene_ending'",
                            },
                            "transition": {
                                "type": "STRING",
                                "description": "The scene ending transition (for example 'FADE TO BLACK')",
                            },
                        },
                        "property_ordering": ["type", "transition"],
                        "required": ["type", "transition"],
                    },
                    {
                        "title": "Dialogue",
                        "type": "OBJECT",
                        "properties": {
                            "type": {
                                "type": "STRING",
                                "description": "Always 'dialogue'",
                            },
                            "character": {
                                "type": "STRING",
                                "description": "The name of the character speaking",
                            },
                            "line": {
                                "type": "STRING",
                                "description": "The dialogue spoken by the character",
                            },
                            "manner": {
                                "type": "STRING",
                                "description": "Describes the way the character delivers the dialogue line. Examples include 'Excitedly,' 'Sadly,' 'Angrily,' 'Quietly,' 'Thoughtfully,' 'Sarcastically,'",
                            },
                        },
                        "property_ordering": [
                            "type",
                            "character",
                            "line",
                            "manner",
                        ],
                        "required": ["type", "character", "line"],
                    },
                ],
            },
        },
    },
}
