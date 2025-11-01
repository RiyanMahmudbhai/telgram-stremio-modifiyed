# Theme configurations based on your color palettes
THEMES = {
    "purple_gradient": {
        "name": "Purple Gradient",
        "colors": {
            "primary": "#A855F7",
            "secondary": "#7C3AED", 
            "accent": "#C084FC",
            "background": "#F8FAFC",
            "card": "#FFFFFF",
            "text": "#1E293B",
            "text_secondary": "#64748B"
        },
        "css_classes": "theme-purple-gradient"
    },
    "blue_navy": {
        "name": "Navy Blue",
        "colors": {
            "primary": "#1E40AF",
            "secondary": "#1E3A8A",
            "accent": "#3B82F6",
            "background": "#F1F5F9",
            "card": "#FFFFFF",
            "text": "#1E293B",
            "text_secondary": "#475569"
        },
        "css_classes": "theme-blue-navy"
    },
    "sunset_warm": {
        "name": "Sunset Warm",
        "colors": {
            "primary": "#F59E0B",
            "secondary": "#DC2626",
            "accent": "#EC4899",
            "background": "#FFFBEB",
            "card": "#FFFFFF",
            "text": "#1F2937",
            "text_secondary": "#6B7280"
        },
        "css_classes": "theme-sunset-warm"
    },
    "ocean_mint": {
        "name": "Ocean Mint",
        "colors": {
            "primary": "#10B981",
            "secondary": "#059669",
            "accent": "#06B6D4",
            "background": "#F0FDF4",
            "card": "#FFFFFF",
            "text": "#1F2937",
            "text_secondary": "#4B5563"
        },
        "css_classes": "theme-ocean-mint"
    },
    "dark_professional": {
        "name": "Dark Professional",
        "colors": {
            "primary": "#06B6D4",
            "secondary": "#0891B2",
            "accent": "#22D3EE",
            "background": "#0F172A",
            "card": "#1E293B",
            "text": "#F8FAFC",
            "text_secondary": "#CBD5E1"
        },
        "css_classes": "theme-dark-professional"
    },
    "crimson_elegance": {
        "name": "Crimson Elegance",
        "colors": {
            "primary": "#DC2626",
            "secondary": "#991B1B",
            "accent": "#F87171",
            "background": "#FEF2F2",
            "card": "#FFFFFF",
            "text": "#1F2937",
            "text_secondary": "#6B7280"
        },
        "css_classes": "theme-crimson-elegance"
    },
    "coral_bliss": {
        "name": "Coral Bliss",
        "colors": {
            "primary": "#FF6B6B",
            "secondary": "#EE5A6F",
            "accent": "#FFB347",
            "background": "#FFF5F5",
            "card": "#FFFFFF",
            "text": "#2D3748",
            "text_secondary": "#718096"
        },
        "css_classes": "theme-coral-bliss"
    },
    "cyber_neon": {
        "name": "Cyber Neon",
        "colors": {
            "primary": "#00FFF0",
            "secondary": "#FF00FF",
            "accent": "#00FF88",
            "background": "#0A0E27",
            "card": "#1A1F3A",
            "text": "#FFFFFF",
            "text_secondary": "#A0AEC0"
        },
        "css_classes": "theme-cyber-neon"
    },
    "forest_earth": {
        "name": "Forest Earth",
        "colors": {
            "primary": "#2D5016",
            "secondary": "#50623A",
            "accent": "#86A789",
            "background": "#F5F5DC",
            "card": "#FFFFFF",
            "text": "#1C1C1C",
            "text_secondary": "#5C5C5C"
        },
        "css_classes": "theme-forest-earth"
    },
    "lavender_dream": {
        "name": "Lavender Dream",
        "colors": {
            "primary": "#B08BBB",
            "secondary": "#9370DB",
            "accent": "#DDA0DD",
            "background": "#FAF5FF",
            "card": "#FFFFFF",
            "text": "#2D3748",
            "text_secondary": "#718096"
        },
        "css_classes": "theme-lavender-dream"
    },
    "golden_luxury": {
        "name": "Golden Luxury",
        "colors": {
            "primary": "#D4AF37",
            "secondary": "#B8860B",
            "accent": "#FFD700",
            "background": "#FFFEF7",
            "card": "#FFFFFF",
            "text": "#1A202C",
            "text_secondary": "#4A5568"
        },
        "css_classes": "theme-golden-luxury"
    },
    "arctic_frost": {
        "name": "Arctic Frost",
        "colors": {
            "primary": "#B0E0E6",
            "secondary": "#4682B4",
            "accent": "#87CEEB",
            "background": "#F0F8FF",
            "card": "#FFFFFF",
            "text": "#1E3A5F",
            "text_secondary": "#5B7C99"
        },
        "css_classes": "theme-arctic-frost"
    },
    "cherry_cola": {
        "name": "Cherry Cola",
        "colors": {
            "primary": "#BF1922",
            "secondary": "#8B0000",
            "accent": "#DC143C",
            "background": "#FFF0F0",
            "card": "#FFFFFF",
            "text": "#1F2937",
            "text_secondary": "#6B7280"
        },
        "css_classes": "theme-cherry-cola"
    },
    "emerald_tech": {
        "name": "Emerald Tech",
        "colors": {
            "primary": "#047857",
            "secondary": "#065F46",
            "accent": "#10B981",
            "background": "#ECFDF5",
            "card": "#FFFFFF",
            "text": "#1F2937",
            "text_secondary": "#4B5563"
        },
        "css_classes": "theme-emerald-tech"
    },
    "midnight_carbon": {
        "name": "Midnight Carbon",
        "colors": {
            "primary": "#3B82F6",
            "secondary": "#1E40AF",
            "accent": "#60A5FA",
            "background": "#111827",
            "card": "#1F2937",
            "text": "#F9FAFB",
            "text_secondary": "#D1D5DB"
        },
        "css_classes": "theme-midnight-carbon"
    }
}


def get_theme(theme_name: str = "purple_gradient"):
    return THEMES.get(theme_name, THEMES["purple_gradient"])


def get_all_themes():
    return THEMES
