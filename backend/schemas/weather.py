from typing import Optional, List
from pydantic import BaseModel

class DailyWeather(BaseModel):
    time: List[str]
    temperature_2m_max: List[Optional[float]]
    precipitation_probability_mean: List[Optional[float]]
    cloudcover_mean: List[Optional[float]]

class WeatherAPIResponse(BaseModel):
    daily: DailyWeather
