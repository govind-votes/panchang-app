import swisseph as swe

# Set path to ephemeris files
swe.set_ephe_path('.')

RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

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

def get_tithi(jd):
    try:
        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
        diff = (moon_lon - sun_lon) % 360
        tithi_num = int(diff / 12) + 1  # 12° per tithi
        return tithi_num
    except Exception as e:
        raise ValueError(f"Error calculating Tithi: {str(e)}")

def get_yoga(jd):
    try:
        sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
        yoga_angle = (sun_lon + moon_lon) % 360
        yoga_num = int(yoga_angle / 13.3333333) + 1  # 27 yogas
        return yoga_num
    except Exception as e:
        raise ValueError(f"Error calculating Yoga: {str(e)}")

def get_karana(jd):
    try:
        tithi_num = get_tithi(jd)
        karana_num = tithi_num * 2 - 1
        karana_name = f"Karana {karana_num}"
        return karana_name
    except Exception as e:
        raise ValueError(f"Error calculating Karana: {str(e)}")

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

        # Panchang elements
        result["tithi"] = get_tithi(jd)
        result["yoga"] = get_yoga(jd)
        result["karana"] = get_karana(jd)

        return result["moon"]
    except Exception as e:
        raise ValueError(f"Error calculating Panchang: {str(e)}")
