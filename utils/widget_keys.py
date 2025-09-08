"""
Generador de keys únicas para widgets de Streamlit
Evita el error StreamlitDuplicateElementId
"""

class WidgetKeyGenerator:
    """
    Generador centralizado de keys únicas para widgets de Streamlit
    """
    
    def __init__(self, module_name: str):
        """
        Inicializa el generador con el nombre del módulo
        
        Args:
            module_name: Nombre del módulo (averias, desempeño, etc.)
        """
        self.module_name = module_name.lower().replace(" ", "_").replace("ñ", "n")
        self.counter = 0
    
    def get_key(self, widget_type: str, description: str = "") -> str:
        """
        Genera una key única para un widget
        
        Args:
            widget_type: Tipo de widget (checkbox, selectbox, slider, etc.)
            description: Descripción opcional del widget
            
        Returns:
            Key única para el widget
        """
        self.counter += 1
        
        # Limpiar descripción para usar en la key
        clean_description = description.lower().replace(" ", "_").replace(":", "").replace("ñ", "n").replace("é", "e").replace("ó", "o")
        
        if clean_description:
            return f"{self.module_name}_{widget_type}_{clean_description}_{self.counter}"
        else:
            return f"{self.module_name}_{widget_type}_{self.counter}"
    
    def checkbox_key(self, description: str = "") -> str:
        """Genera key para checkbox"""
        return self.get_key("checkbox", description)
    
    def selectbox_key(self, description: str = "") -> str:
        """Genera key para selectbox"""
        return self.get_key("selectbox", description)
    
    def multiselect_key(self, description: str = "") -> str:
        """Genera key para multiselect"""
        return self.get_key("multiselect", description)
    
    def slider_key(self, description: str = "") -> str:
        """Genera key para slider"""
        return self.get_key("slider", description)
    
    def radio_key(self, description: str = "") -> str:
        """Genera key para radio"""
        return self.get_key("radio", description)
    
    def text_input_key(self, description: str = "") -> str:
        """Genera key para text_input"""
        return self.get_key("text_input", description)
    
    def date_input_key(self, description: str = "") -> str:
        """Genera key para date_input"""
        return self.get_key("date_input", description)
    
    def button_key(self, description: str = "") -> str:
        """Genera key para button"""
        return self.get_key("button", description)
    
    def download_button_key(self, description: str = "") -> str:
        """Genera key para download_button"""
        return self.get_key("download_button", description)


# Generadores pre-configurados para cada módulo
AVERIAS_KEYS = WidgetKeyGenerator("averias")
DESEMPENO_KEYS = WidgetKeyGenerator("desempeno")
CONFIGURATION_KEYS = WidgetKeyGenerator("configuration")
PROVISION_KEYS = WidgetKeyGenerator("provision")
DISPONIBILIDAD_KEYS = WidgetKeyGenerator("disponibilidad")
CALIDAD_KEYS = WidgetKeyGenerator("calidad")
PROYECTOS_KEYS = WidgetKeyGenerator("proyectos")
APP_KEYS = WidgetKeyGenerator("app")


def get_module_keys(module_name: str) -> WidgetKeyGenerator:
    """
    Obtiene el generador de keys para un módulo específico
    
    Args:
        module_name: Nombre del módulo
        
    Returns:
        Generador de keys para el módulo
    """
    module_generators = {
        "averias": AVERIAS_KEYS,
        "desempeno": DESEMPENO_KEYS,
        "desempeño": DESEMPENO_KEYS,
        "configuration": CONFIGURATION_KEYS,
        "provision": PROVISION_KEYS,
        "disponibilidad": DISPONIBILIDAD_KEYS,
        "calidad": CALIDAD_KEYS,
        "proyectos": PROYECTOS_KEYS,
        "app": APP_KEYS
    }
    
    return module_generators.get(module_name.lower(), WidgetKeyGenerator(module_name))