# FORM VALIDATION - ADMIN UI
# Validates form fields and manages error states, border colors, and
# error message labels for the admin dashboard.

ERROR_COLOR = "#A64C42"


# def set_field_state() - Applies the correct border color to a form field
# based on whether it is valid (valid: default color) or invalid
# (invalid: error color).
def set_field_state(field, invalid: bool) -> None:
	if not hasattr(field, "_validation_default_border"):
		field._validation_default_border = field.cget("border_color")
	field.configure(
		border_color=(
			ERROR_COLOR if invalid else field._validation_default_border
		)
	)


# def set_field_error() - Sets or clears the validation error message displayed
# below a form field, and applies the validation state accordingly.
def set_field_error(field, feedback, message: str) -> None:
	if not hasattr(feedback, "_validation_default_text_color"):
		feedback._validation_default_text_color = feedback.cget("text_color")
	set_field_state(field, bool(message))
	if message:
		feedback.grid()
	else:
		feedback.grid_remove()
	feedback.configure(
		text=message,
		text_color=(
			ERROR_COLOR if message else feedback._validation_default_text_color
		),
	)
