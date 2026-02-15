import re

def parse_uk_postcode(postcode: str):
    """
    Normalize and dissect a UK postcode.

    Returns a dictionary with:
    - postcode_normalized: cleaned full postcode (e.g. 'SW1A 1AA')
    - area: postcode area (e.g. 'SW')
    - district: postcode district (e.g. 'SW1A')
    - sector: postcode sector (e.g. 'SW1A 1')
    - unit: postcode unit (e.g. '1AA')
    """

    if not postcode or not postcode.strip():
        return None  # or raise ValueError("Empty postcode")

    # Step 1: Remove leading/trailing spaces, convert to uppercase
    postcode_clean = postcode.strip().upper()

    # Step 2: Ensure a single space between outward and inward code
    postcode_clean = re.sub(r"\s+", "", postcode_clean)  # remove all spaces
    postcode_clean = postcode_clean[:-3] + " " + postcode_clean[-3:]  # insert space before last 3 chars

    # Step 3: Parse outward and inward codes using regex
    match = re.match(r"^([A-Z]{1,2}\d[A-Z\d]?)[ ]?(\d[A-Z]{2})$", postcode_clean)
    if not match:
        raise ValueError(f"Invalid UK postcode format: {postcode}")

    outward, inward = match.groups()

    # Step 4: Extract components
    area_match = re.match(r"^[A-Z]{1,2}", outward)
    area = area_match.group() if area_match else outward  # e.g., 'SW'

    district = outward  # e.g., 'SW1A'
    sector = f"{outward} {inward[0]}"  # e.g., 'SW1A 1'
    #unit = inward[1:]  # e.g., 'AA'

    postcode_normalized = f"{outward} {inward}"

    return {
        'Postcode': {
            "postcode_full": postcode_normalized,
            "postcode_area": area,
            "postcode_district": district,
            "postcode_sector": sector
        }
    }
