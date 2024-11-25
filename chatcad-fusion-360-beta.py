import sys
import os
import adsk.core, adsk.fusion, adsk.cam, traceback

# Get the directory of the current script
script_dir = os.path.dirname(os.path.realpath(__file__))

# Add the 'lib' directory to sys.path
lib_dir = os.path.join(script_dir, 'lib')
sys.path.insert(0, lib_dir)

# Import OpenAI with compatibility for different versions
import openai
from openai import OpenAI

# Retrieve the API key from the environment variable
api_key = os.environ.get('OPENAI_API_KEY')

if not api_key:
    raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

handlers = []

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Get the Utilities tab
        utilities_tab = ui.allToolbarTabs.itemById('ToolsTab')
        if not utilities_tab:
            ui.messageBox('Utilities tab not found.')
            return

        # Create a new panel in the Utilities tab if it doesn't exist
        panel_id = 'ChatCADPanel'
        chat_panel = utilities_tab.toolbarPanels.itemById(panel_id)
        if not chat_panel:
            chat_panel = utilities_tab.toolbarPanels.add(panel_id, 'ChatCAD')

        # Create a new command definition
        command_id = 'ChatCADCommand'
        cmd_def = ui.commandDefinitions.itemById(command_id)
        if not cmd_def:
            cmd_def = ui.commandDefinitions.addButtonDefinition(
                command_id,
                'ChatCAD Input',
                'Shows a pop-up with a text input field',
                ''  # Assuming you have icons in a 'Resources' folder
            )

        # Add the button to the panel
        button = chat_panel.controls.itemById(command_id)
        if not button:
            button = chat_panel.controls.addCommand(cmd_def)

        # Connect the command created event
        on_command_created = MyCommandCreatedHandler()
        cmd_def.commandCreated.add(on_command_created)
        handlers.append(on_command_created)

    except:
        if ui:
            ui.messageBox('Failed in run:\n{}'.format(traceback.format_exc()))
        else:
            print('Failed in run:\n{}'.format(traceback.format_exc()))

    adsk.autoTerminate(False)  # Place this outside the try-except block

def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Remove the panel and command
        utilities_tab = ui.allToolbarTabs.itemById('ToolsTab')
        panel = utilities_tab.toolbarPanels.itemById('ChatCADPanel')
        if panel:
            panel.deleteMe()

        cmd_def = ui.commandDefinitions.itemById('ChatCADCommand')
        if cmd_def:
            cmd_def.deleteMe()

    except:
        if ui:
            ui.messageBox('Failed in stop:\n{}'.format(traceback.format_exc()))
        else:
            print('Failed in stop:\n{}'.format(traceback.format_exc()))

class MyCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            event_args = adsk.core.CommandCreatedEventArgs.cast(args)
            command = event_args.command
            inputs = command.commandInputs

            # Create a text input field
            text_input = inputs.addStringValueInput('text_input', 'Enter Text: Create a ...', '')

            # Debugging: Confirm input field creation
            # ui = adsk.core.Application.get().userInterface
            # ui.messageBox('Input Field Created')

            # Connect the execute event
            on_execute = MyCommandExecuteHandler()
            command.execute.add(on_execute)
            handlers.append(on_execute)

        except:
            ui = adsk.core.Application.get().userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            event_args = adsk.core.CommandEventArgs.cast(args)
            inputs = event_args.command.commandInputs

            # Retrieve the text input value
            user_input = inputs.itemById('text_input').value

            # Call the ChatGPT API with the user's input
            script = generate_chatgpt_response(user_input)

            # Clean the generated script
            cleaned_script = clean_script(script)

            # Show the cleaned script for confirmation
            ui = adsk.core.Application.get().userInterface
            response = ui.messageBox(
                'Generated Script:\n\n' + cleaned_script + '\n\nDo you want to run this script?',
                'Script Confirmation',
                adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                adsk.core.MessageBoxIconTypes.QuestionIconType
            )

             # If the user confirms, execute the cleaned script
            if response == adsk.core.DialogResults.DialogYes:
                try:
                    # Execute the script
                    exec(cleaned_script, globals())
                    # Call the run function from the executed script
                    run(event_args)
                except Exception as e:
                    ui.messageBox('An error occurred while executing the script:\n{}'.format(str(e)))
            else:
                ui.messageBox('Script execution cancelled.')

        except:
            ui = adsk.core.Application.get().userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def clean_script(script):
    lines = script.splitlines()
    # Remove the first and last lines if there are at least 3 lines
    if len(lines) > 2:
        cleaned_lines = lines[1:-1]
    else:
        # If there are less than 3 lines, return as-is to avoid losing content
        cleaned_lines = lines
    return "\n".join(cleaned_lines)


def generate_chatgpt_response(user_input):
    try:
        prompt = f"""
You are a Fusion 360 expert. Write a Python script that works in Fusion 360's API environment to generate 
the following geometry: {user_input}. 
Only provide the Python script. Do not include ANY extra words or characters before or after the script. 
Before you give an output, take your time to think about how to approach modeling the desired geometry, 
deciding what basic features make up the desired geometry, and using best practices for 3D CAD modelling.

For example, if the user input is:
"Create a mounting plate 5in by 6in with 0.25in bolt holes on the corners, 0.3in filleted vertical edges, 
and a 1in square hole through the center"

Then the output should be:
import adsk.core, adsk.fusion, adsk.cam, traceback
def run(context):
    try:
        # Get the application and user interface
        app = adsk.core.Application.get()
        ui = app.userInterface
        # Get the active design
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active Fusion design', 'Error')
            return
        # Get the root component
        rootComp = design.rootComponent
        # Create a new sketch on the XY plane
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        sketch = sketches.add(xyPlane)
        # Define parameters
        width = 5.0  # inches
        height = 6.0  # inches
        thickness = 0.25  # inches
        holeDiameter = 0.25  # inches
        cornerFilletRadius = 0.3  # inches
        centerHoleSize = 1.0  # inches
        # Draw rectangle centered at origin
        recLines = sketch.sketchCurves.sketchLines
        rectangle = recLines.addCenterPointRectangle(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(width / 2, height / 2, 0)
        )
        # Extrude the profile
        prof = sketch.profiles.item(0)
        extrudes = rootComp.features.extrudeFeatures
        extInput = extrudes.createInput(
            prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        distance = adsk.core.ValueInput.createByReal(thickness)
        extInput.setDistanceExtent(False, distance)
        ext = extrudes.add(extInput)
        body = ext.bodies.item(0)
        # Apply fillets to vertical edges only
        fillets = rootComp.features.filletFeatures
        filletInput = fillets.createInput()
        edges = adsk.core.ObjectCollection.create()
        # Collect vertical edges
        for edge in body.edges:
            edgeGeom = edge.geometry
            if isinstance(edgeGeom, adsk.core.Line3D):
                startPoint = edge.startVertex.geometry
                endPoint = edge.endVertex.geometry
                dirVec = startPoint.vectorTo(endPoint)
                dirVec.normalize()
                # Check if the edge is vertical
                if abs(dirVec.x) < 1e-3 and abs(dirVec.y) < 1e-3:
                    edges.add(edge)
        if edges.count > 0:
            filletRadius = adsk.core.ValueInput.createByReal(cornerFilletRadius)
            filletInput.addConstantRadiusEdgeSet(edges, filletRadius, False)
            fillets.add(filletInput)
        # Add bolt holes at corners
        holeSketch = sketches.add(xyPlane)
        circles = holeSketch.sketchCurves.sketchCircles
        holePositions = [
            adsk.core.Point3D.create(-width / 2 + cornerFilletRadius, -height / 2 + cornerFilletRadius, 0),
            adsk.core.Point3D.create(width / 2 - cornerFilletRadius, -height / 2 + cornerFilletRadius, 0),
            adsk.core.Point3D.create(width / 2 - cornerFilletRadius, height / 2 - cornerFilletRadius, 0),
            adsk.core.Point3D.create(-width / 2 + cornerFilletRadius, height / 2 - cornerFilletRadius, 0)
        ]
        for pos in holePositions:
            circles.addByCenterRadius(pos, holeDiameter / 2)
        # Cut the holes
        holeProfiles = adsk.core.ObjectCollection.create()
        for profile in holeSketch.profiles:
            holeProfiles.add(profile)
        extInput = extrudes.createInput(
            holeProfiles, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        distance = adsk.core.ValueInput.createByReal(thickness)
        extInput.setDistanceExtent(False, distance)
        extInput.participantBodies = [body]
        extrudes.add(extInput)
        # Add center square hole
        squareSketch = sketches.add(xyPlane)
        squareSize = centerHoleSize
        squareLines = squareSketch.sketchCurves.sketchLines
        p0 = adsk.core.Point3D.create(-squareSize / 2, -squareSize / 2, 0)
        p1 = adsk.core.Point3D.create(squareSize / 2, -squareSize / 2, 0)
        p2 = adsk.core.Point3D.create(squareSize / 2, squareSize / 2, 0)
        p3 = adsk.core.Point3D.create(-squareSize / 2, squareSize / 2, 0)
        squareLines.addByTwoPoints(p0, p1)
        squareLines.addByTwoPoints(p1, p2)
        squareLines.addByTwoPoints(p2, p3)
        squareLines.addByTwoPoints(p3, p0)
        # Cut the square hole
        squareProf = squareSketch.profiles.item(0)
        extInput = extrudes.createInput(
            squareProf, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        distance = adsk.core.ValueInput.createByReal(thickness)
        extInput.setDistanceExtent(False, distance)
        extInput.participantBodies = [body]
        extrudes.add(extInput)
    except:
        if ui:
            ui.messageBox('Failed:\\n'.format(traceback.format_exc()))
"""

            
        

        response = client.chat.completions.create(
            model="o1-preview",
            messages=[
                #{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=20000
        )
        response_message = response.choices[0].message.content

        # return full_response.strip()
        return response_message.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Global list to keep handlers referenced
handlers = []
