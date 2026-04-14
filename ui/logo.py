from __future__ import annotations

import customtkinter as ctk


class SimpleLogo(ctk.CTkCanvas):
    def __init__(self, master, size: int = 28, bg_color: str = "#0B1324", **kwargs):
        super().__init__(
            master,
            width=size,
            height=size,
            bg=bg_color,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )

        pad = max(3, int(size * 0.14))
        stroke_outer = max(2, int(size * 0.07))
        stroke_inner = max(2, int(size * 0.06))

        self.create_polygon(
            size / 2, pad,
            size - pad, size / 2,
            size / 2, size - pad,
            pad, size / 2,
            outline="#32A1FF",
            fill="",
            width=stroke_outer,
        )

        inner = size * 0.18
        self.create_rectangle(
            size / 2 - inner / 2,
            size / 2 - inner / 2,
            size / 2 + inner / 2,
            size / 2 + inner / 2,
            outline="#32A1FF",
            fill="",
            width=stroke_inner,
        )


class BrandBlock(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str = "Print Consultor",
        subtitle: str = "Consulta e consolidação de logs",
        fg_color: str = "transparent",
        bg_color_for_logo: str = "#0B1324",
        **kwargs,
    ):
        super().__init__(master, fg_color=fg_color, **kwargs)

        icon_top = ctk.CTkFrame(self, fg_color="transparent")
        icon_top.pack(anchor="w", pady=(0, 10))

        self.logo_icon_small = SimpleLogo(icon_top, size=22, bg_color=bg_color_for_logo)
        self.logo_icon_small.pack(side="left")

        logo_full = ctk.CTkFrame(self, fg_color="transparent")
        logo_full.pack(anchor="w")

        self.logo_icon_main = SimpleLogo(logo_full, size=28, bg_color=bg_color_for_logo)
        self.logo_icon_main.pack(side="left", padx=(0, 10))

        text_wrap = ctk.CTkFrame(logo_full, fg_color="transparent")
        text_wrap.pack(side="left")

        self.title_label = ctk.CTkLabel(
            text_wrap,
            text=title,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#F2F6FF",
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color="#8DA3D1",
        )
        self.subtitle_label.pack(anchor="w", pady=(6, 0))