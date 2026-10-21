// Moves an element to the end of <body> while it's on the page (and takes it
// away with it). Used by the printable run sheet, so printing can drop
// everything else on the page (routes/layout.css) without hiding the sheet.
export function portal(node: HTMLElement) {
	document.body.appendChild(node);

	return {
		destroy() {
			node.remove();
		}
	};
}
