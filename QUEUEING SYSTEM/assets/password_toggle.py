"""Vector eye toggle button for masked password fields.

The icon is drawn directly on a tkinter canvas so it renders crisply at every
size and follows the CustomTkinter light/dark appearance mode, instead of
relying on emoji glyphs (which Tk renders inconsistently across platforms).
"""

import math
import tkinter
from typing import Any, Callable, Optional, Union

import customtkinter as ctk


# Icon states.
CLOSED = "closed"  # password hidden  -> closed eyelid with lashes
OPEN = "open"      # password visible -> open eye with pupil and lashes

EYE_COLOR = ("#4A5A4E", "#C3D2C5")
EYE_HOVER_COLOR = ("#2F6639", "#8FC79A")

# Width reserved for the toggle inside the entry.
TOGGLE_SIZE = 30


class PasswordVisibilityButton(ctk.CTkButton):
	"""Transparent button that renders a vector eye / closed-eyelid icon.

	Use :meth:`set_state` to switch between the masked and visible icons.
	"""

	def __init__(
		self,
		master: Any,
		command: Optional[Callable[[], Any]] = None,
		width: int = 34,
		height: int = 34,
		color: Union[str, tuple] = EYE_COLOR,
		hover_color: Union[str, tuple] = EYE_HOVER_COLOR,
		state: str = CLOSED,
		**kwargs: Any,
	) -> None:
		self._eye_color = color
		self._eye_hover_color = hover_color
		self._eye_state = state
		self._eye_items: list = []

		super().__init__(
			master,
			text="",
			width=width,
			height=height,
			fg_color="transparent",
			hover_color=hover_color,
			command=command,
			**kwargs,
		)

		# The stock button only paints its rounded rectangle, so the vector
		# icon is layered on top of the very same canvas the button draws on.
		self._draw_eye()

	def set_state(self, state: str) -> None:
		"""Switch the icon between the ``closed`` and ``open`` variants."""
		if state not in (CLOSED, OPEN):
			raise ValueError(f"unknown password icon state: {state!r}")
		if state == self._eye_state:
			return
		self._eye_state = state
		self._draw_eye()

	def get_state(self) -> str:
		return self._eye_state

	# ------------------------------------------------------------------
	# drawing
	# ------------------------------------------------------------------
	def _eye_color_for_state(self) -> str:
		color = self._eye_hover_color if self._mouse_inside else self._eye_color
		return self._apply_appearance_mode(color)

	def _draw_eye(self) -> None:
		canvas = self._canvas
		for item in self._eye_items:
			canvas.delete(item)
		self._eye_items = []

		scale = self._apply_widget_scaling(1)
		width = self._apply_widget_scaling(self._current_width)
		height = self._apply_widget_scaling(self._current_height)

		# Keep the glyph inside the button with a small breathing margin.
		margin = 3 * scale
		size = min(width, height) - 2 * margin
		if size <= 0:
			return

		center_x = width / 2
		center_y = height / 2
		color = self._eye_color_for_state()

		if self._eye_state == OPEN:
			self._eye_items = self._draw_open_eye(canvas, center_x, center_y, size, color, scale)
		else:
			self._eye_items = self._draw_closed_eye(canvas, center_x, center_y, size, color, scale)

		self._eye_items = [item for item in self._eye_items if item is not None]

	def _draw_open_eye(self, canvas, center_x, center_y, size, color, scale):
		"""Almond shaped eye outline with a filled pupil and lashes on top."""
		items = []
		half_width = size / 2
		half_height = size * 0.26
		stroke = max(1, round(1.8 * scale))

		# Eye outline as a closed curve: two quadratic bezier arcs.
		lid_points = self._bezier_arc(
			center_x - half_width, center_y,
			center_x, center_y - half_height,
			center_x + half_width, center_y,
			steps=26,
		)
		lid_points += self._bezier_arc(
			center_x + half_width, center_y,
			center_x, center_y + half_height,
			center_x - half_width, center_y,
			steps=26,
		)
		items.append(
			canvas.create_polygon(
				lid_points,
				smooth=True,
				fill="",
				outline=color,
				width=stroke,
			)
		)

		# Pupil
		pupil_radius = size * 0.16
		items.append(
			canvas.create_oval(
				center_x - pupil_radius, center_y - pupil_radius,
				center_x + pupil_radius, center_y + pupil_radius,
				fill=color, outline=color,
			)
		)

		# Highlight inside the pupil
		highlight_radius = pupil_radius * 0.32
		highlight_x = center_x - pupil_radius * 0.36
		highlight_y = center_y - pupil_radius * 0.36
		items.append(
			canvas.create_oval(
				highlight_x - highlight_radius, highlight_y - highlight_radius,
				highlight_x + highlight_radius, highlight_y + highlight_radius,
				fill=self._apply_appearance_mode(self._bg_color),
				outline=self._apply_appearance_mode(self._bg_color),
			)
		)

		items.extend(self._draw_lashes(canvas, center_x, center_y, half_width, half_height, color, scale, upper=True))
		return items

	def _draw_closed_eye(self, canvas, center_x, center_y, size, color, scale):
		"""Downward curved eyelid with lashes hanging below it."""
		items = []
		half_width = size / 2
		half_height = size * 0.30

		# The lid is a shallow "U": the corners sit high, the middle dips low.
		lid_points = self._bezier_arc(
			center_x - half_width, center_y - half_height * 0.5,
			center_x, center_y + half_height,
			center_x + half_width, center_y - half_height * 0.5,
			steps=34,
		)
		items.append(
			canvas.create_line(
				lid_points,
				fill=color,
				width=max(1, round(2.2 * scale)),
				capstyle=tkinter.ROUND,
				smooth=True,
			)
		)

		items.extend(self._draw_lashes(canvas, center_x, center_y, half_width, half_height, color, scale, upper=False))
		return items

	def _draw_lashes(self, canvas, center_x, center_y, half_width, half_height, color, scale, upper: bool):
		"""Short strokes radiating away from the eyelid."""
		items = []
		lash_count = 7
		width = max(1, round(1.6 * scale))

		for index in range(lash_count):
			fraction = (index + 0.5) / lash_count
			# Position along the lid, mirrored around the centre.
			x = center_x - half_width + (2 * half_width) * fraction
			# Lid height at that x position (parabolic approximation).
			normalized = (x - center_x) / half_width if half_width else 0.0
			curve = 1.0 - normalized * normalized

			if upper:
				# Lashes sit on the upper lid and fan outwards.
				y = center_y - half_height * curve
				direction = -1.0
			else:
				# The closed lid dips down, so the lashes start on the curve.
				y = center_y + half_height * (0.5 - 1.0 * curve)
				direction = 1.0

			# Lashes splay outward and are longest near the middle.
			splay = (fraction - 0.5) * 2.0
			length = half_height * 1.15 * (1.0 - 0.2 * abs(splay))
			dx = splay * length * 0.55
			dy = direction * length * 0.85

			items.append(
				canvas.create_line(
					x, y,
					x + dx, y + dy,
					fill=color,
					width=width,
					capstyle=tkinter.ROUND,
				)
			)
		return items

	@staticmethod
	def _bezier_arc(x0, y0, x1, y1, x2, y2, steps: int = 24):
		"""Quadratic bezier sample points from (x0, y0) via (x1, y1) to (x2, y2)."""
		points = []
		for step in range(steps + 1):
			t = step / steps
			inv = 1.0 - t
			x = inv * inv * x0 + 2 * inv * t * x1 + t * t * x2
			y = inv * inv * y0 + 2 * inv * t * y1 + t * t * y2
			points.append(x)
			points.append(y)
		return points

	# ------------------------------------------------------------------
	# customtkinter hooks
	# ------------------------------------------------------------------
	def _draw(self, no_color_updates: bool = False) -> None:
		super()._draw(no_color_updates)
		if hasattr(self, "_eye_items"):
			self._draw_eye()

	def _on_enter(self, event=None) -> None:
		super()._on_enter(event)
		self._draw_eye()

	def _on_leave(self, event=None) -> None:
		super()._on_leave(event)
		self._draw_eye()

	def _set_scaling(self, *args, **kwargs) -> None:
		super()._set_scaling(*args, **kwargs)
		self._draw_eye()

	def _set_appearance_mode(self, mode_string: str) -> None:
		super()._set_appearance_mode(mode_string)
		self._draw_eye()
