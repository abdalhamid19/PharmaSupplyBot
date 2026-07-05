"""Manufacturer extraction logic for drug names."""

import re

# Known pharmaceutical manufacturers in Egypt
KNOWN_MANUFACTURERS = {
    'ORCHIDIA', 'ORA', 'EVA', 'PHARCO', 'AMOUN', 'EIPICO', 
    'MARCYRL', 'SIGMA', 'SANOFI', 'NOVARTIS', 'PFIZER',
    'MEPACO', 'SEDICO', 'OCTOBER', 'ADWIA', 'DELTA',
    'GLAXO', 'KAHIRA', 'MEMPHIS', 'AMRIYA', 'HIKMA',
    'BAYER', 'MERCK', 'ROCHE', 'SPIMACO', 'JULPHAR',
    'GSK', 'SANDOZ', 'TEVA', 'MASH', 'INAD',
}


def extract_manufacturer_from_name(name: str) -> tuple[str, str | None]:
    """
    Extract manufacturer from drug name, returning (base_name, manufacturer).
    
    Extraction priority:
    1. From parentheses like (ORCHIDIA)
    2. From known manufacturer list at end of name
    3. None if not found
    
    Examples:
        "METHYL FOLATE 30 CAP ORCHIDIA" → ("METHYL FOLATE 30 CAP", "ORCHIDIA")
        "METHYL FOLATE (ORCHIDIA) 30 CAPS" → ("METHYL FOLATE 30 CAPS", "ORCHIDIA")
        "ASPIRIN 100 MG TABLETS" → ("ASPIRIN 100 MG TABLETS", None)
    """
    if not name:
        return name, None
    
    name_upper = name.upper().strip()
    
    # 1. Extract from parentheses first
    paren_match = re.search(r'\(([A-Z]+)\)', name_upper)
    if paren_match:
        manufacturer = paren_match.group(1)
        if manufacturer in KNOWN_MANUFACTURERS:
            # Remove parentheses and manufacturer
            base_name = re.sub(r'\s*\([A-Z]+\)\s*', ' ', name, flags=re.IGNORECASE).strip()
            # Clean up multiple spaces
            base_name = re.sub(r'\s+', ' ', base_name)
            return base_name, manufacturer
    
    # 2. Check for known manufacturer in the name
    tokens = name_upper.split()
    
    # Scan all tokens for known manufacturers (prefer later tokens)
    manufacturer_positions = []
    for i, token in enumerate(tokens):
        if token in KNOWN_MANUFACTURERS:
            manufacturer_positions.append(i)
    
    # If found, use the last occurrence (most likely to be manufacturer)
    if manufacturer_positions:
        mfr_idx = manufacturer_positions[-1]
        manufacturer = tokens[mfr_idx]
        # Reconstruct base name without manufacturer
        base_tokens = tokens[:mfr_idx] + tokens[mfr_idx+1:]
        base_name = ' '.join(base_tokens)
        return base_name, manufacturer
    
    return name, None


__all__ = [
    'extract_manufacturer_from_name',
    'KNOWN_MANUFACTURERS',
]
