from __future__ import annotations

import customtkinter as ctk


class DashboardCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        value: str = "-",
        subtitle: str = "",
        accent: str = "#4B8BFF",
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color="#121B2E",
            corner_radius=14,
            border_width=1,
            border_color="#223153",
            **kwargs,
        )
        self.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(
            self,
            text=title.upper(),
            font=ctk.CTkFont(size=11),
            text_color="#7C92C5",
            anchor="w",
        )
        self.lbl_title.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))

        self.lbl_value = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=accent,
            anchor="w",
        )
        self.lbl_value.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 2))

        self.lbl_subtitle = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color="#9AAACC",
            anchor="w",
        )
        self.lbl_subtitle.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))

    def set(self, value: str, subtitle: str = "") -> None:
        self.lbl_value.configure(text=value)
        self.lbl_subtitle.configure(text=subtitle)


class ActionButton(ctk.CTkButton):
    def __init__(self, master, text: str, command, primary: bool = False, **kwargs):
        fg = "#4B8BFF" if primary else "#151F34"
        hover = "#3D73D2" if primary else "#1D2C49"
        border = "#4B8BFF" if primary else "#25375A"

        super().__init__(
            master,
            text=text,
            command=command,
            height=44,
            corner_radius=10,
            fg_color=fg,
            hover_color=hover,
            border_width=1,
            border_color=border,
            text_color="#EAF1FF",
            anchor="w",
            font=ctk.CTkFont(size=14),
            **kwargs,
        )