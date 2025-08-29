from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Opioid Conversion Calculator")

templates = Jinja2Templates(directory="templates")

openai.api_key = os.getenv("OPENAI_API_KEY")

class OpioidMedication(BaseModel):
    drug: str
    route: str
    dose: float
    units: str
    frequency: Optional[str] = None

class OpioidRegimen(BaseModel):
    medications: List[OpioidMedication]

class ConversionRequest(BaseModel):
    regimen: OpioidRegimen
    target_drug: str
    target_route: str = "po"

class ConversionResult(BaseModel):
    total_ome: float
    target_drug: str
    target_route: str
    target_dose: float
    target_units: str

class ParseRequest(BaseModel):
    text: str

class ParseResponse(BaseModel):
    regimen: OpioidRegimen

class ConversionEngine:
    def __init__(self):
        self.conversion_data = self._load_conversion_data()
    
    def _load_conversion_data(self) -> Dict[str, Any]:
        with open("conversion.json", "r") as f:
            return json.load(f)
    
    def calculate_ome(self, regimen: OpioidRegimen) -> float:
        total_ome = 0.0
        
        for i, med in enumerate(regimen.medications):
            print(f"  Med {i+1}: {med.drug} {med.dose} {med.units} {med.route} frequency='{med.frequency}'")
            
            conversion_factor = self._get_conversion_factor(
                med.drug.lower(), 
                med.route.lower(), 
                med.units
            )
            print(f"  Conversion factor: {conversion_factor}")
            
            if conversion_factor:
                daily_dose = self._calculate_daily_dose(med)
                print(f"  Daily dose: {daily_dose}")
                med_ome = daily_dose * conversion_factor
                print(f"  Med OME: {med_ome}")
                total_ome += med_ome
        
        return total_ome
    
    def _get_conversion_factor(self, drug: str, route: str, units: str) -> Optional[float]:
        # Map input units to daily units for lookup in conversion table
        target_unit = None
        if units in ["mg", "mg/day"]:
            target_unit = "mg/day"
        elif units in ["mcg", "mcg/day"]:
            target_unit = "mcg/day"
        elif units == "mcg/hr":
            target_unit = "mcg/hr"
        elif units == "mg/hr":
            target_unit = "mg/hr"
        
        if not target_unit:
            print(f"⚠️  Unknown unit type: {units}")
            return None
            
        for record in self.conversion_data["records"]:
            if (record["drug"] == drug and 
                record["route"] == route and 
                record["dose_unit"] == target_unit):
                return record["to_ome"]
        return None
    
    def _calculate_daily_dose(self, med: OpioidMedication) -> float:
        # For hourly rates (mcg/hr, mg/hr), don't multiply by frequency
        if med.units in ["mcg/hr", "mg/hr"]:
            print(f"    Hourly rate detected, using dose as-is: {med.dose} {med.units}")
            return med.dose
            
        # For single doses (mg, mcg), multiply by frequency to get daily dose
        if med.frequency:
            freq_map = {
                "once daily": 1, "daily": 1, "qd": 1,
                "twice daily": 2, "bid": 2, "q12h": 2,
                "three times daily": 3, "tid": 3, "q8h": 3,
                "four times daily": 4, "qid": 4, "q6h": 4,
                "every 4 hours": 6, "q4h": 6, "every 6 hours": 4, "q6h": 4,
                "every 8 hours": 3, "every 12 hours": 2,
                "prn": 1, "as needed": 1
            }
            multiplier = freq_map.get(med.frequency.lower(), 1)
            print(f"    Frequency '{med.frequency}' -> multiplier {multiplier}")
            print(f"    Converting {med.dose} {med.units} to daily dose: {med.dose * multiplier}")
            return med.dose * multiplier
            
        print(f"    No frequency specified, using dose as daily: {med.dose} {med.units}")
        return med.dose
    
    def convert_from_ome(self, ome_total: float, target_drug: str, target_route: str = "po") -> ConversionResult:
        print(f"🎯 Looking for target: {target_drug.lower()} + {target_route.lower()} + mg/day")
        conversion_factor = self._get_conversion_factor(target_drug.lower(), target_route.lower(), "mg/day")
        print(f"🔍 Found conversion factor: {conversion_factor}")
        
        if conversion_factor:
            target_dose = ome_total / conversion_factor
            print(f"✅ Converted {ome_total} OME to {target_dose:.2f} mg/day {target_drug}")
            return ConversionResult(
                total_ome=ome_total,
                target_drug=target_drug,
                target_route=target_route,
                target_dose=target_dose,
                target_units="mg/day"
            )
        
        print(f"❌ No conversion factor found, defaulting to morphine")
        return ConversionResult(
            total_ome=ome_total,
            target_drug="morphine",
            target_route="po", 
            target_dose=ome_total,
            target_units="mg/day"
        )

conversion_engine = ConversionEngine()

@app.post("/parse", response_model=ParseResponse)
async def parse_natural_language(request: ParseRequest):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
            
        client = openai.AsyncOpenAI()
        
        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical assistant that parses opioid medication descriptions into structured data. 
                    Extract medications, routes, doses, units, and frequencies from natural language.
                    
                    CRITICAL: Only parse what is explicitly stated. DO NOT perform any calculations or conversions.
                    
                    Example: "0.2mg hydromorphone every 6 hours" should parse as:
                    - dose: 0.2 (not 0.8)
                    - units: "mg" (not "mg/day")
                    - frequency: "every 6 hours"
                    
                    Return JSON with medications array containing drug, route, dose, units, and frequency fields."""
                },
                {
                    "role": "user", 
                    "content": f"Parse this opioid regimen: {request.text}"
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "opioid_regimen",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "medications": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "drug": {
                                            "type": "string",
                                            "enum": ["morphine", "oxycodone", "hydromorphone", "fentanyl", "methadone", "buprenorphine", "tramadol", "codeine", "hydrocodone", "oxymorphone", "levorphanol", "meperidine", "pentazocine", "tapentadol", "butorphanol", "diamorphine", "sufentanil", "pethidine", "dextropropoxyphene", "dihydrocodeine"]
                                        },
                                        "route": {
                                            "type": "string",
                                            "enum": ["po", "iv", "im", "sc", "transdermal", "buc_sublingual", "rectal"]
                                        },
                                        "dose": {"type": "number"},
                                        "units": {
                                            "type": "string",
                                            "enum": ["mg", "mcg", "mg/hr", "mcg/hr"]
                                        },
                                        "frequency": {
                                            "type": "string",
                                            "enum": ["daily", "twice daily", "three times daily", "four times daily", "every 4 hours", "every 6 hours", "every 8 hours", "every 12 hours", "q4h", "q6h", "q8h", "q12h", "bid", "tid", "qid", "prn", "as needed"]
                                        }
                                    },
                                    "required": ["drug", "route", "dose", "units"]
                                }
                            }
                        },
                        "required": ["medications"]
                    }
                }
            }
        )
        
        # Log the raw OpenAI response
        raw_response = response.choices[0].message.content
        print(f"🤖 OpenAI Raw Response: {raw_response}")
        
        parsed_data = json.loads(raw_response)
        print(f"📊 Parsed Data: {parsed_data}")
        
        # Normalize drug names to lowercase for consistency with conversion table
        for med in parsed_data['medications']:
            med['drug'] = med['drug'].lower()
        
        regimen = OpioidRegimen(**parsed_data)
        print(f"✅ Final Regimen: {regimen}")
        
        return ParseResponse(regimen=regimen)
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to parse medication text. The AI model returned invalid JSON. Please try rephrasing your input.")
    except openai.RateLimitError:
        print("OpenAI rate limit exceeded")
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    except openai.AuthenticationError:
        print("OpenAI authentication error")
        raise HTTPException(status_code=500, detail="API authentication failed. Please contact support.")
    except Exception as e:
        print(f"Parse error: {str(e)}")
        error_msg = str(e)
        if "enum" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Unrecognized medication, route, units, or frequency. Please check your input and try again.")
        elif "required" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Missing required medication information (drug, route, dose, or units). Please provide complete medication details.")
        else:
            raise HTTPException(status_code=500, detail=f"Unable to parse medication text: {error_msg}")

@app.post("/convert", response_model=ConversionResult)
async def convert_opioids(request: ConversionRequest):
    try:
        print(f"🔄 Converting regimen: {request.regimen}")
        print(f"🎯 Target: {request.target_drug} ({request.target_route})")
        
        total_ome = conversion_engine.calculate_ome(request.regimen)
        print(f"💊 Total OME calculated: {total_ome}")
        
        result = conversion_engine.convert_from_ome(
            total_ome, 
            request.target_drug, 
            request.target_route
        )
        print(f"📋 Conversion result: {result}")
        
        return result
    except Exception as e:
        print(f"Convert error: {str(e)}")
        error_msg = str(e)
        if "conversion factor" in error_msg.lower():
            raise HTTPException(status_code=400, detail="No conversion data available for one or more medications in your regimen. Please check drug names, routes, and units.")
        elif "target" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Invalid target medication or route specified for conversion.")
        else:
            raise HTTPException(status_code=500, detail=f"Conversion failed: {error_msg}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
