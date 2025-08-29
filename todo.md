# Opioid Conversion POC - Todo List

The purpose of this app is to allow a user to voice input a drug and route, and get a conversion to OME. We use uv to manage the project, and as a package manager. Openai is used for the LLM, to convert the voice input to a structured query. The conversion table is stored in a json file, and is used to convert the drug and route to OME. There is an endpoint to parse the voice input, and an endpoint to convert the drug and route to OME.

we use daisyui as a component library, and alpine.js for the frontend reactivity.

## Backend Tasks
- [x] Set up FastAPI backend with OpenAI integration and Pydantic models
- [x] Create opioid conversion tables and OME calculation engine
- [x] Build /parse endpoint for LLM natural language structuring
- [x] Build /convert endpoint for OME calculations and target drug conversion

## Frontend Tasks
- [x] Create HTML templates with DaisyUI styling and voice input components
- [x] Implement Web Speech API for voice-to-text with visual feedback
- [x] Create editable results table with drug/route/units/dose dropdowns
- [ ] Convert to Alpine.js for reactive frontend state management

## Testing & Deployment
- [x] Test voice input accuracy with medical terminology and conversion calculations
- [x] Add error handling and cross-browser compatibility

## ✅ COMPLETED - Ready to Use!

The application is now running at http://localhost:8000 with:
- Voice input support with visual feedback
- Natural language parsing via OpenAI
- Accurate OME calculations using clinical conversion tables
- Beautiful DaisyUI interface
- Editable results table for manual corrections
- Two-endpoint architecture (/parse and /convert)

To run: `OPENAI_API_KEY=your_key uv run python main.py`
- [ ] Implement Web Speech API for voice-to-text with visual feedback
- [ ] Create editable results table with drug/route/units/dose dropdowns
- [ ] Integrate HTMX for seamless form submission and result display

## Testing & Deployment
- [ ] Test voice input accuracy with medical terminology and conversion calculations
- [ ] Add error handling and cross-browser compatibility

## Progress Notes
- Dependencies already installed: uvicorn, fastapi, openai, pydantic
- Starting with backend FastAPI setup