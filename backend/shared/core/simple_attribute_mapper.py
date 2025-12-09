"""
Simple Attribute Mapper - 100% System-Agnostic
Generates mechanical codes from attribute names without semantic analysis
"""

import re
from typing import Dict, List, Tuple


class UniversalCodeGenerator:
    """
    100% system-agnostic: generates codes purely from attribute names
    No semantic analysis, no common attribute assumptions
    """
    
    def __init__(self):
        self.existing_codes = set()
    
    def generate_code(self, attr_name: str) -> str:
        """
        Pure mechanical approach:
        "health" -> "hea"
        "shield_capacity" -> "shi" 
        "quantum_flux_reactor" -> "qua"
        "xj_9_biological_matrix" -> "xj9"
        
        No interpretation, just mechanical code generation
        """
        
        # Clean name: remove special chars, convert to lowercase
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', attr_name.lower())
        
        # Take first available characters (3 preferred, fallback to 2-4)
        if len(clean_name) >= 3:
            base_code = clean_name[:3]
        elif len(clean_name) >= 2:
            base_code = clean_name[:2]
        else:
            # Single character: repeat to make 2 chars
            base_code = clean_name + clean_name if clean_name else "aa"
        
        # Ensure uniqueness
        final_code = self.ensure_unique(base_code)
        return final_code
    
    def ensure_unique(self, base_code: str) -> str:
        """
        Simple collision resolution: extend by 1 character at a time
        "hea" -> "hea1" -> "hea2" -> "hea3"
        No semantic meaning, just uniqueness
        """
        
        if base_code not in self.existing_codes:
            self.existing_codes.add(base_code)
            return base_code
            
        counter = 1
        while f"{base_code}{counter}" in self.existing_codes:
            counter += 1
        
        unique_code = f"{base_code}{counter}"
        self.existing_codes.add(unique_code)
        return unique_code
    
    def reset_codes(self):
        """Reset the existing codes set for new processing session"""
        self.existing_codes.clear()


class SimpleAttributeMapper:
    """
    Takes attribute names as given, creates 3-4 letter codes dynamically
    NO semantic classification or grouping
    """
    
    def __init__(self):
        self.code_generator = UniversalCodeGenerator()
        self.attribute_mapping = {}  # code -> full_name
        self.reverse_mapping = {}   # full_name -> code
    
    def map_attributes(self, attributes: Dict[str, any]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Map attribute names to compact codes
        
        Returns:
            Tuple of (code_mapping, reverse_mapping)
            code_mapping: {attribute_name: code}
            reverse_mapping: {code: attribute_name}
        """
        
        code_mapping = {}
        reverse_mapping = {}
        
        # Reset code generator for fresh mapping
        self.code_generator.reset_codes()
        
        for attr_name in attributes.keys():
            if attr_name not in self.reverse_mapping:  # Avoid duplicates
                code = self.code_generator.generate_code(attr_name)
                code_mapping[attr_name] = code
                reverse_mapping[code] = attr_name
                
                # Store in instance for reference
                self.attribute_mapping[code] = attr_name
                self.reverse_mapping[attr_name] = code
        
        return code_mapping, reverse_mapping
    
    def get_code_mapping(self) -> Dict[str, str]:
        """Get current code -> attribute name mapping"""
        return self.attribute_mapping.copy()
    
    def get_reverse_mapping(self) -> Dict[str, str]:
        """Get current attribute name -> code mapping"""
        return self.reverse_mapping.copy()
    
    def apply_code_mapping(self, data: Dict[str, any], code_mapping: Dict[str, str]) -> Dict[str, any]:
        """
        Apply code mapping to transform attribute names to compact codes
        
        Args:
            data: Original data with full attribute names
            code_mapping: Mapping from attribute names to codes
            
        Returns:
            Data with attribute names replaced by codes
        """
        
        if not isinstance(data, dict):
            return data
        
        mapped_data = {}
        
        for key, value in data.items():
            if key in code_mapping:
                mapped_data[code_mapping[key]] = value
            else:
                mapped_data[key] = value
        
        return mapped_data


# Example usage and testing
if __name__ == "__main__":
    # Test the system with various attribute names
    test_attributes = {
        "health": 100,
        "armor_class": 15,
        "speed": 30,
        "strength": 18,
        "shield_capacity": 50,
        "quantum_flux_reactor": 75,
        "xj_9_biological_matrix": 25,
        "healing": 10,  # Should get hea1 due to collision with "health"
        "armored": 5,    # Should get arm1 due to collision with "armor_class"
    }
    
    mapper = SimpleAttributeMapper()
    code_map, reverse_map = mapper.map_attributes(test_attributes)
    
    print("Original Attributes:", list(test_attributes.keys()))
    print("Code Mapping:", code_map)
    print("Reverse Mapping:", reverse_map)
    
    # Test application of mapping
    mapped_data = mapper.apply_code_mapping(test_attributes, code_map)
    print("Mapped Data:", mapped_data)
