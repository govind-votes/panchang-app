import swisseph as swe
import os
from datetime import datetime, timedelta, timezone

# Set path to ephemeris files
EPHE_PATH = os.path.join(os.path.dirname(__file__), "ephe")
swe.set_ephe_path(EPHE_PATH)

# Rashi Names
RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Nakshatra Names
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

# Panet Names
PLANETS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mars": swe.MARS,
    "mercury": swe.MERCURY,
    "jupiter": swe.JUPITER,
    "venus": swe.VENUS,
    "saturn": swe.SATURN,
    "rahu": swe.MEAN_NODE,  # Rahu (North Node)
    "ketu": swe.MEAN_NODE   # Ketu (180° from Rahu)
}

# Tithi Names (1–30)
TITHIS = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Amavasya"
]

# Paksha Names
PAKSHA = ["Shukla", "Krishna"]

# Yoga Names (27)
YOGAS = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma",
    "Dhriti","Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra",
    "Siddhi","Vyatipada","Variyan","Parigha","Shiva","Siddha","Sadhya","Shubha",
    "Shukla","Brahma","Indra","Vaidhriti"
]

# Karana Names (11 unique, repeat cycle)
KARANAS = [
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Shakuni","Chatushpada","Naga","Kimstughna"
]

def get_rashi(longitude, jd):
    try:
        ayan = swe.get_ayanamsa_ut(jd)
        sidereal_long = (longitude - ayan) % 360
        index = int(sidereal_long // 30)
        return RASHIS[index], sidereal_long
    except Exception as e:
        raise ValueError(f"Error calculating Rashi: {str(e)}")

def get_nakshatra(longitude, jd):
    try:
        ayan = swe.get_ayanamsa_ut(jd)
        sidereal_long = (longitude - ayan) % 360
        index = int(sidereal_long // (360 / 27))
        pada = int((sidereal_long % (360 / 27)) // (360 / 108)) + 1
        return NAKSHATRAS[index], pada, sidereal_long
    except Exception as e:
        raise ValueError(f"Error calculating Nakshatra: {str(e)}")

def get_lagna(jd, lat, lon):
    try:
        lag = swe.houses(jd, lat, lon)[0][0]  # Ascendant
        ayan = swe.get_ayanamsa_ut(jd)
        sidereal_long = (lag - ayan) % 360
        index = int(sidereal_long // 30)
        return RASHIS[index], sidereal_long
    except Exception as e:
        raise ValueError(f"Error calculating Lagna: {str(e)}")

def get_tithi_details(jd):
    try:
        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]

        diff = (moon_lon - sun_lon) % 360
        tithi_num = int(diff / 12) + 1  # 1–30

        # Tithi name
        tithi_name = TITHIS[tithi_num - 1]

        # Paksha
        paksha = "Shukla" if tithi_num <= 15 else "Krishna"

        return tithi_num, tithi_name, paksha
    except Exception as e:
        raise ValueError(f"Error calculating Tithi: {str(e)}")

def get_yoga_name(jd):
    try:
        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
        ayan = swe.get_ayanamsa_ut(jd)

        sun_sidereal = (sun_lon - ayan) % 360
        moon_sidereal = (moon_lon - ayan) % 360

        yoga_angle = (sun_sidereal + moon_sidereal) % 360
        yoga_num = int(yoga_angle / (360 / 27))

        return yoga_num + 1, YOGAS[yoga_num]
    except Exception as e:
        raise ValueError(f"Error calculating Yoga: {str(e)}")

def get_karana_name(jd):
    try:
        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
        diff = (moon_lon - sun_lon) % 360

        karana_number = int(diff // 6)  # 0–59

        repeating = ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"]

        if karana_number == 0:
            return "Kimstughna"
        elif 1 <= karana_number <= 56:
            return repeating[(karana_number - 1) % 7]
        else:
            fixed = ["Shakuni", "Chatushpada", "Naga", "Kimstughna"]
            return fixed[karana_number - 57]
    except Exception as e:
        raise ValueError(f"Error calculating Karana: {str(e)}")

def get_var(jd,tz_offset=5.5):
    try:
        local_jd = jd + tz_offset/24
        weekday = swe.day_of_week(local_jd)
        VARAS = ["Somavara", "Mangalavara", "Budhavara",
                "Guruvara", "Shukravara", "Shanivara","Ravivara"]
        return VARAS[weekday]
    except Exception as e:
        raise ValueError(f"Error calculating Var: {str(e)}")

def get_masa(jd):
    try:
        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        ayan = swe.get_ayanamsa_ut(jd)
        sidereal_sun = (sun_lon - ayan) % 360
        masa_num = int(sidereal_sun // 30)

        MASA = [
            "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
            "Ashwin", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna"
        ]
        return MASA[masa_num]
    except Exception as e:
        raise ValueError(f"Error calculating Masa: {str(e)}")
    
def jd_to_local_time(jd, tz_offset):
    """Convert Julian Day to local datetime string"""
    if jd is None:
        return None

    # Convert JD → UTC datetime
    utc_dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=(jd - 2440587.5))

    # Convert UTC → local timezone
    local_dt = utc_dt + timedelta(hours=tz_offset)

    return local_dt.strftime("%H:%M:%S")
    
def get_sunrise_sunset(year, month, day, lat, lon, tz_offset=5.5):
    try:
        # swe.rise_trans: 1 = rise, 2 = set
        jd_start = swe.julday(year, month, day, 0)
        geopos = [lon, lat, 0]  # longitude, latitude, altitude
        sunrise_jd= swe.rise_trans(jd_start, swe.SUN, 1, geopos)[1][0]
        sunset_jd  = swe.rise_trans(jd_start, swe.SUN, 2, geopos)[1][0]

        # Convert JD to local time (default IST: UTC+5:30)
        sunrise_local = jd_to_local_time(sunrise_jd, tz_offset)
        sunset_local = jd_to_local_time(sunset_jd, tz_offset)

        return sunrise_local, sunset_local
    except Exception as e:
        raise ValueError(f"Error calculating sunrise_sunset: {str(e)}")
    


def get_planet_positions(year, month, day, hour, lat, lon):
    try:
        jd = swe.julday(year, month, day, hour)
        result = {}

        # Lagna
        lagna_rashi, lagna_sid = get_lagna(jd, lat, lon)
        result["lagna"] = {"rashi": lagna_rashi, "sidereal_longitude": lagna_sid}

        # Moon Nakshatra only in return for now
        moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
        moon_nak, moon_pada, _ = get_nakshatra(moon_lon, jd)
        result["moon"] = {"nakshatra": moon_nak, "pada": moon_pada}

        # --- Panchang details ---
        tithi_num, tithi_name, paksha = get_tithi_details(jd)
        yoga_num, yoga_name = get_yoga_name(jd)
        karana_name = get_karana_name(jd)
        masa = get_masa(jd)
        vara = get_var(jd)
        sunrise, sunset = get_sunrise_sunset(year, month, day, lat, lon)
        

        return {
                    "lagna": result["lagna"],
                    "moon": result["moon"],
                    "tithi": {"number": tithi_num, "name": tithi_name, "paksha": paksha},
                    "masa": masa,
                    "var": vara,
                    "yoga": {"number": yoga_num, "name": yoga_name},
                    "karana": karana_name,
                    "sunrise": sunrise,
                    "sunset": sunset
                }
    except Exception as e:
        raise ValueError(f"Error calculating Panchang: {str(e)}")
