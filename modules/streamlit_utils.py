from PIL import Image 
import streamlit as st
from streamlit.components.v1 import html
import os
import base64
import re

CSS_UNITS = ['cm', 'mm', 'in', 'px', 'pt', 'pc', 'em', 'ex', 'ch', 'rem', 'vw', 'vh', 'vmin', 'vmax', '%']

def add_image(image, caption="", width=0, height=0):
    if type(image) == str:
        if not os.path.isfile(image):
            st.error(f"Image {image} not found")
            return
        image = Image.open(image)
    
    if 'PIL.' not in str(type(image)):
        try:
            image = Image.fromarray(image)
        except:
            st.error("Could not convert image to pillow image")
            return
    
    # Resize unless width or height are 0
    if width * height:
        image.resize((width, height))
    
    # Render w/ caption
    st.image(image, caption=caption, use_column_width=True)

def load_css(css_path):
    if '//' in css_path: # external url
        st.markdown(f'<link href="{css_path}" rel="stylesheet">', unsafe_allow_html=True);
    elif os.path.isfile(css_path):
        st.markdown(f'<style>{open(css_path).read()}</style>', unsafe_allow_html=True);
        
def svg_write(svg, center=True):
    """
    Disable center to left-margin align like other objects.
    """
    # Encode as base 64
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    # Add some CSS on top
    css_justify = "center" if center else "left"
    css = f'<p style="text-align:center; display: flex; justify-content: {css_justify};">'
    html = f'{css}<img src="data:image/svg+xml;base64,{b64}"/>'

    # Write the HTML
    st.write(html, unsafe_allow_html=True)

uuid = 0
def inject_js(script):
    """
    Injects script into the streamlit page
    
    Really hard to get right, so I'm just going to leave this here.
    ALL RIGHTS RESERVED LEON LEIBMANN 2023
    """
    global uuid
    
    # Use iframe breaking to inject directly to the head
    # https://stackoverflow.com/questions/67223608/how-can-an-iframe-remove-its-own-sandboxing
    # Lucicrously, this is the only way to inject JS anywhere on the page
    uuid_str = str(uuid)
    uuid += 1
    
    #//root.innerHTML += `<script id=injected-{uuid} type="text/javascript">{script}<\/script>`
    if '`' in script:
        print("WARNING: ` in script, may cause injection errors")
    
    script_inject = """
        <script type="text/javascript">
        // Injection Script
        let parent = window.parent;
        let injected = parent.document.getElementById("injected-{uuid}");
        if (injected == null) {
            let root = parent.document.getElementById("portal");
            
            var script = parent.document.createElement("script");
            script.type = "text/javascript";
            script.innerHTML = `{script}`;
            root.appendChild(script);
        }
        
        // Now make self invisible
        
        var elements = parent.document.querySelectorAll("*");
        for (var i = 0; i < elements.length; i++) {
            var element = elements[i];

            // Check if the element has only one child, which is an iframe
            if (element.children.length === 1 && element.children[0].tagName === "IFRAME")
                // Ensure the iframe has height=0
                if(element.children[0].getAttribute("height") === "0")
                    element.style.display = "none";
            
        }
        
        </script>
        """.replace("{script}", script).replace("{uuid}", uuid_str)
    html(script_inject, height=0, width=0,)

headers_map = {}
def header(text, element="h2"):
    """
    Creates a header in both the sidebar and the main page.
    The sidebar's header is an anchor link to scroll to the main page's header.
    This sidebar element becomes bold if this is the current section.
    
    HOLY HELL THIS WAS NEXT LEVEL HARD
    THEREFORE THIS METHOD AND INJECT_JS, IS 
    ALL RIGHTS RESERVED LEON LEIBMANN 2023
    """
    global headers_map
    elem_id = text.lower().strip().replace(" ", "-")
    anchor_id = f"__anchor-{elem_id}"
    headers_map[elem_id] = len(headers_map)
    
    # Create the header itself (not in the sidebar)
    st.markdown(f'<{element} id="{elem_id}" >{text}</{element}>', unsafe_allow_html=True)
    
    # Calculate header level
    header_level = re.sub(r'\D', '', element)
    header_level = int(header_level) if header_level else 2
    header_level = max(2, min(6, header_level))
    header_level -= 1
    
    # Create sidebar anchor link
    st.sidebar.markdown(f"""
        <button  id={anchor_id} class="fake-button" style="padding-left: {header_level}em;">
        {text}
        </button>
        """,
    unsafe_allow_html=True)
    
    # Inject JS that keeps track of the current section,
    # marked when this header is passed the verticle halfway mark
    
    if True:
        inject_js("""
                console.log("hello");
                var current_header = current_header || 0;
                var headers_map = headers_map || new Map();
                
                // Add scroll event listeners to all elements
                var elements = document.querySelectorAll(".stApp");

                // TODO: fix worlds hackiest on scroll event listener
                setInterval(function() {
                    // Iterate over all headers in map
                    for (var elem_id in headers_map) {
                        var elem = document.getElementById(elem_id);
                        if (elem == null) continue;
                        if (elem.getBoundingClientRect().top < window.innerHeight / 2) {
                             current_header = elem_id;
                        }
                    }
                    
                    // Make current header bold
                    var corresponding_anchor = document.getElementById("__anchor-" + current_header);
                    if (corresponding_anchor) corresponding_anchor.classList.add("anchor-bold");
                    
                    // Make all other anchors nonbold
                    var other_anchors = document.querySelectorAll(".anchor-bold:not(#__anchor-"+ current_header+")");
                    for (var i = 0; i < other_anchors.length; i++)
                        other_anchors[i].classList.remove("anchor-bold");
                }, 100);
                
                // Util function to scroll to a header
                function scrollToElement(elementId) {
                    var element = document.getElementById(elementId);

                    // Check if the element exists
                    if (element) {
                        // Scroll to the element
                        element.scrollIntoView({ behavior: "smooth" });
                    }
                }
            """.replace("{elem_id}", elem_id)
        )
        
        # Inject correct styling for bold "anchor"s
        st.markdown(
            """
            <style>
                .anchor-bold {
                    transform: translateX(10px) !important; /* currently doesnt work */
                    font-weight: bold;
                }
                .fake-button {
                    /* Remove button styling */
                    border: none;
                    padding: 0;
                    color: lightblue;
                    background: none;
                    transition: transform 0.3s ease, font-weight 0.3s ease;
                    height:0;
                    -webkit-tap-highlight-color: transparent;
                }
                .fake-button:focus,.fake-button:visited,.fake-button:active{
                    outline: none;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
    
    # Ensure this header is in the JS header map.
    # Also, while we're at it, inject on click listener to fakeanchor to scroll to this header
    inject_js(f"""
              headers_map['{elem_id}'] = headers_map.size
              document.getElementById("{anchor_id}").addEventListener("click", function() 
              """ + "{" + f"""
                scrollToElement("{elem_id}");
              """ + "}" + ");"
            )
    
    
def render_draggable(raw_html, zoom_factor:float=1.0, container_height:str="500px", initial_position:tuple=("0px", "60%"), background_color:str="white"):
    """
    Renders raw HTML in a draggable container.
    """
    
    # Quick initial position validation
    if len(initial_position) != 2:
        raise ValueError("initial_position must be a tuple of 2 elements")

    initial_position = list(initial_position)
    initial_position = [str(x).strip() for x in initial_position]
    initial_position = [x if re.search(f"({'|'.join(CSS_UNITS)})$", x) else f"{x}px" for x in initial_position]
    
    # Wrap the html
    wrapped = f"""
         <div id="container" style='overflow: hidden; width: 100%; height: 100%; position: fixed; background-color:{background_color}; top:0; bottom:0; left:0; right:0;'>
            <div id="draggable" style='position: absolute; transform: scale({zoom_factor}); transform-origin: 50% 50%; top: calc(50% + -1000px + {initial_position[0]}); left: calc(50% + -1000px + {initial_position[1]}); width: 2000px; height: 2000px; display: flex; align-items: center; justify-content: center;'>
                {raw_html}
            </div>
        </div>
    """
    
    # Inject JS to make it draggable
    script = """
    <script>
    window.onload = function() {
        draggable(document.getElementById('draggable'));
    }

    function draggable(el) {
        el.style.cursor = "grab"
        el.addEventListener('mousedown', function(e) {
            el.classList.add('active');
            el.style.cursor = "grabbing"
            
            var offsetX = e.clientX - parseInt(window.getComputedStyle(this).left);
            var offsetY = e.clientY - parseInt(window.getComputedStyle(this).top);
            
            function mouseMoveHandler(e) {
                el.style.top = (e.clientY - offsetY) + 'px';
                el.style.left = (e.clientX - offsetX) + 'px';
            }

            function reset() {
                el.classList.remove('active');
                el.style.cursor = "grab"
                window.removeEventListener('mousemove', mouseMoveHandler);
                window.removeEventListener('mouseup', reset);
            }

            window.addEventListener('mousemove', mouseMoveHandler);
            window.addEventListener('mouseup', reset);
        });
    }
    </script>
    """
    
    # Add style to ensure cursor is a grab
    style = """
    <style>
        #draggable.active {
            cursor: grabbing !important;
            /*filter: brightness(0.8);*/
        }
    </style>
    """
    
    # Inject the script and style
    # Iframe actually helps us here
    html(wrapped + script + style, height=int(container_height[:-2]))