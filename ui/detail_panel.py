from __future__ import annotations

from typing import Callable, List, Tuple

import customtkinter as ctk


SummaryItems = List[Tuple[str, str]]


class DetailPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_tab_change: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color="#0C1325",
            corner_radius=14,
            border_width=1,
            border_color="#1C2945",
            **kwargs,
        )
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._on_tab_change = on_tab_change
        self.current_tab = "Resumo"

        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 10))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            header,
            text="Painel de contexto",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#F2F6FF",
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.segmented = ctk.CTkSegmentedButton(
            header,
            values=["Resumo", "Campos brutos", "Consolidado"],
            command=self._handle_tab_change,
            selected_color="#2A4F87",
            selected_hover_color="#2A4F87",
            unselected_color="#131D31",
            unselected_hover_color="#182640",
            text_color="#DCE6FB",
            corner_radius=10,
        )
        self.segmented.grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.segmented.set(self.current_tab)

    def _build_body(self) -> None:
        self.body = ctk.CTkFrame(
            self,
            fg_color="#09101F",
            corner_radius=12,
            border_width=1,
            border_color="#1D2942",
        )
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(
            self.body,
            fg_color="transparent",
        )
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.empty_label = None
        self.set_empty_state("Selecione um log para ver o resumo.")

    def _handle_tab_change(self, value: str) -> None:
        self.current_tab = value
        self._on_tab_change(value)

    def clear(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()

    def set_empty_state(self, text: str) -> None:
        self.clear()
        self.empty_label = ctk.CTkLabel(
            self.scroll,
            text=text,
            text_color="#9AAACC",
            font=ctk.CTkFont(size=13),
            justify="left",
            wraplength=420,
            anchor="w",
        )
        self.empty_label.pack(fill="x", anchor="w", padx=4, pady=6)

    def render_summary_block(self, title: str, items: SummaryItems) -> None:
        self.clear()

        title_label = ctk.CTkLabel(
            self.scroll,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#F2F6FF",
            anchor="w",
            justify="left",
            wraplength=420,
        )
        title_label.pack(fill="x", anchor="w", padx=4, pady=(4, 14))

        for label, value in items:
            block = ctk.CTkFrame(
                self.scroll,
                fg_color="transparent",
            )
            block.pack(fill="x", anchor="w", padx=4, pady=(0, 12))

            label_widget = ctk.CTkLabel(
                block,
                text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#DCE6FB",
                anchor="w",
                justify="left",
                wraplength=420,
            )
            label_widget.pack(fill="x", anchor="w")

            value_widget = ctk.CTkLabel(
                block,
                text=value,
                font=ctk.CTkFont(size=13),
                text_color="#B8C7E6",
                anchor="w",
                justify="left",
                wraplength=420,
            )
            value_widget.pack(fill="x", anchor="w", pady=(4, 0))

    def render_raw_text(self, title: str, text: str) -> None:
        self.clear()

        title_label = ctk.CTkLabel(
            self.scroll,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#F2F6FF",
            anchor="w",
        )
        title_label.pack(fill="x", anchor="w", padx=4, pady=(4, 14))

        text_box = ctk.CTkTextbox(
            self.scroll,
            fg_color="#0B1324",
            border_width=1,
            border_color="#1D2942",
            text_color="#E8EEFB",
            font=("Consolas", 12),
            corner_radius=10,
            wrap="word",
            height=520,
        )
        text_box.pack(fill="both", expand=True, anchor="w", padx=4, pady=(0, 4))
        text_box.insert("1.0", text)
        text_box.configure(state="disabled")