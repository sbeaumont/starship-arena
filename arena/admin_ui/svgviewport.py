"""
SVG Viewport wrapper for interactive pan/zoom functionality.

Separates SVG generation from HTML/JavaScript presentation concerns.
Serge Beaumont / Claude, 2025
"""


class SVGViewport:
    """Wraps an SVG with interactive pan/zoom HTML/JavaScript controls."""
    
    def __init__(self, svg_content: str):
        """Initialize with SVG content string."""
        self.svg_content = svg_content
    
    def to_html(self, container_id: str = "svg-viewport") -> str:
        """Generate HTML wrapper with pan/zoom functionality."""
        # Extract viewBox from SVG to calculate aspect ratio
        import re
        viewbox_match = re.search(r'viewBox="([^"]*)"', self.svg_content)
        if viewbox_match:
            viewbox_values = viewbox_match.group(1).split()
            if len(viewbox_values) >= 4:
                width = float(viewbox_values[2])
                height = float(viewbox_values[3])
                aspect_ratio = height / width if width > 0 else 1
            else:
                aspect_ratio = 1
        else:
            aspect_ratio = 1
        
        # Modify SVG to have 100% width and proper height
        svg_with_full_width = self.svg_content.replace(
            '<svg ', 
            f'<svg width="100%" height="{int(100 * aspect_ratio)}%" style="cursor: grab; display: block; max-height: 80vh;" '
        )
        
        # Add ID if not present
        if 'id=' not in svg_with_full_width:
            svg_with_full_width = svg_with_full_width.replace('<svg ', f'<svg id="{container_id}-svg" ')
        
        # Convert dashes to underscores for valid JavaScript function names
        js_func_prefix = container_id.replace('-', '_')
        
        html = f'''<div class="svg-container" id="{container_id}" style="width: 100%; position: relative;">
    <div class="svg-controls" style="position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(0,0,0,0.7); padding: 5px; border-radius: 3px;">
        <button onclick="{js_func_prefix}_zoomIn()" style="margin: 2px; color: white; background: #444; border: 1px solid #666; padding: 4px 8px; cursor: pointer;">+</button>
        <button onclick="{js_func_prefix}_zoomOut()" style="margin: 2px; color: white; background: #444; border: 1px solid #666; padding: 4px 8px; cursor: pointer;">-</button>
        <button onclick="{js_func_prefix}_resetView()" style="margin: 2px; color: white; background: #444; border: 1px solid #666; padding: 4px 8px; cursor: pointer;">Reset</button>
    </div>
    {svg_with_full_width}
</div>
<script>
(function() {{
    function initViewport() {{
    let currentScale = 1;
    let currentTranslateX = 0;
    let currentTranslateY = 0;
    let isDragging = false;
    let startX, startY;

    const svg = document.getElementById('{container_id}-svg') || document.querySelector('#{container_id} svg');
    if (!svg) {{
        console.log('SVG element not found');
        return;
    }}
    
    const initialViewBox = svg.getAttribute('viewBox').split(' ').map(Number);
    const [initialX, initialY, initialWidth, initialHeight] = initialViewBox;

    // Check for initial viewport data
    const initialViewportAttr = svg.getAttribute('data-initial-viewport');
    if (initialViewportAttr) {{
        const [vpX1, vpY1, vpX2, vpY2] = initialViewportAttr.split(',').map(Number);
        const vpWidth = Math.abs(vpX2 - vpX1);
        const vpHeight = Math.abs(vpY2 - vpY1);
        const vpCenterX = (vpX1 + vpX2) / 2;
        const vpCenterY = (vpY1 + vpY2) / 2;
        
        // Calculate scale to fit viewport area nicely
        const scaleX = initialWidth / (vpWidth * 1.5);
        const scaleY = initialHeight / (vpHeight * 1.5);
        currentScale = Math.min(scaleX, scaleY, 8);
        currentScale = Math.max(currentScale, 1.5);
        
        // Calculate new viewBox dimensions after scaling
        const newWidth = initialWidth / currentScale;
        const newHeight = initialHeight / currentScale;
        
        // Center the viewport on the ship path area
        currentTranslateX = vpCenterX - newWidth / 2;
        currentTranslateY = vpCenterY - newHeight / 2;
    }}

    function updateViewBox() {{
        const newWidth = initialWidth / currentScale;
        const newHeight = initialHeight / currentScale;
        const newX = currentTranslateX;
        const newY = currentTranslateY;
        svg.setAttribute('viewBox', `${{newX}} ${{newY}} ${{newWidth}} ${{newHeight}}`);
    }}
    
    // Apply initial viewport
    updateViewBox();

    window.{js_func_prefix}_zoomIn = function() {{
        currentScale *= 1.3;
        updateViewBox();
    }};

    window.{js_func_prefix}_zoomOut = function() {{
        currentScale /= 1.3;
        updateViewBox();
    }};

    window.{js_func_prefix}_resetView = function() {{
        currentScale = 1;
        currentTranslateX = 0;
        currentTranslateY = 0;
        updateViewBox();
    }};

    // Mouse wheel zoom at cursor position
    svg.addEventListener('wheel', function(e) {{
        e.preventDefault();
        
        // Get the actual rendered size and position of SVG content (same as drag logic)
        const rect = svg.getBoundingClientRect();
        const svgAspectRatio = initialHeight / initialWidth;
        const containerAspectRatio = rect.height / rect.width;
        
        let actualSVGWidth, actualSVGHeight, svgOffsetX, svgOffsetY;
        
        if (svgAspectRatio > containerAspectRatio) {{
            // SVG is taller - limited by height, centered horizontally
            actualSVGHeight = rect.height;
            actualSVGWidth = rect.height / svgAspectRatio;
            svgOffsetX = (rect.width - actualSVGWidth) / 2;
            svgOffsetY = 0;
        }} else {{
            // SVG is wider - limited by width, centered vertically  
            actualSVGWidth = rect.width;
            actualSVGHeight = rect.width * svgAspectRatio;
            svgOffsetX = 0;
            svgOffsetY = (rect.height - actualSVGHeight) / 2;
        }}
        
        // Calculate mouse position relative to actual SVG content area
        const mouseRatioX = (e.clientX - rect.left - svgOffsetX) / actualSVGWidth;
        const mouseRatioY = (e.clientY - rect.top - svgOffsetY) / actualSVGHeight;
        
        // Calculate mouse position in current SVG coordinates
        const currentViewWidth = initialWidth / currentScale;
        const currentViewHeight = initialHeight / currentScale;
        const mouseSVGX = currentTranslateX + mouseRatioX * currentViewWidth;
        const mouseSVGY = currentTranslateY + mouseRatioY * currentViewHeight;
        
        // Apply zoom
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        currentScale *= delta;
        
        // Calculate new view dimensions
        const newViewWidth = initialWidth / currentScale;
        const newViewHeight = initialHeight / currentScale;
        
        // Adjust translation to keep mouse position fixed
        currentTranslateX = mouseSVGX - mouseRatioX * newViewWidth;
        currentTranslateY = mouseSVGY - mouseRatioY * newViewHeight;
        
        updateViewBox();
    }});

    // Mouse drag panning - direct 1:1 movement
    svg.addEventListener('mousedown', function(e) {{
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        svg.style.cursor = 'grabbing';
    }});

    document.addEventListener('mousemove', function(e) {{
        if (!isDragging) return;
        
        const pixelMoveX = e.clientX - startX;
        const pixelMoveY = e.clientY - startY;
        
        // Get the actual rendered size and position of SVG content
        const rect = svg.getBoundingClientRect();
        const svgAspectRatio = initialHeight / initialWidth;
        const containerAspectRatio = rect.height / rect.width;
        
        let actualSVGWidth, actualSVGHeight, svgOffsetX, svgOffsetY;
        
        if (svgAspectRatio > containerAspectRatio) {{
            // SVG is taller - limited by height, centered horizontally
            actualSVGHeight = rect.height;
            actualSVGWidth = rect.height / svgAspectRatio;
            svgOffsetX = (rect.width - actualSVGWidth) / 2;
            svgOffsetY = 0;
        }} else {{
            // SVG is wider - limited by width, centered vertically  
            actualSVGWidth = rect.width;
            actualSVGHeight = rect.width * svgAspectRatio;
            svgOffsetX = 0;
            svgOffsetY = (rect.height - actualSVGHeight) / 2;
        }}
        
        // Convert pixel movement to SVG units using actual SVG dimensions
        const currentViewWidth = initialWidth / currentScale;
        const currentViewHeight = initialHeight / currentScale;
        
        const svgMoveX = pixelMoveX * (currentViewWidth / actualSVGWidth);
        const svgMoveY = pixelMoveY * (currentViewHeight / actualSVGHeight);
        
        currentTranslateX -= svgMoveX;
        currentTranslateY -= svgMoveY;
        
        startX = e.clientX;
        startY = e.clientY;
        
        updateViewBox();
    }});

    document.addEventListener('mouseup', function() {{
        isDragging = false;
        svg.style.cursor = 'grab';
    }});

    // Touch support for mobile
    let initialDistance = 0;
    let initialScale = 1;

    svg.addEventListener('touchstart', function(e) {{
        if (e.touches.length === 2) {{
            initialDistance = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
            initialScale = currentScale;
        }} else if (e.touches.length === 1) {{
            isDragging = true;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }}
    }});

    svg.addEventListener('touchmove', function(e) {{
        e.preventDefault();
        
        if (e.touches.length === 2) {{
            const currentDistance = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
            currentScale = initialScale * (currentDistance / initialDistance);
            updateViewBox();
        }} else if (e.touches.length === 1 && isDragging) {{
            const dx = (e.touches[0].clientX - startX) * (initialWidth / svg.clientWidth) / currentScale;
            const dy = (e.touches[0].clientY - startY) * (initialHeight / svg.clientHeight) / currentScale;
            
            currentTranslateX -= dx;
            currentTranslateY -= dy;
            
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            
            updateViewBox();
        }}
    }});

    svg.addEventListener('touchend', function() {{
        isDragging = false;
    }});
    }}
    
    // Initialize when DOM is ready or immediately if already ready
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', initViewport);
    }} else {{
        initViewport();
    }}
}})();
</script>'''
        
        return html