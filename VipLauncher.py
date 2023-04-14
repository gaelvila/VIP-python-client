from __future__ import annotations
import os
import time
from pathlib import *
import json

import vip

"""
Main Features (leading to public methods)
A. Manage a Session from start to finish, *i.e.*:
    A.1. Login to VIP
    A.2. Upload the input data on VIP
    A.3. Launch executions on VIP
    A.4. Monitor executions on VIP
    A.5. Download the results from VIP
    A.6. Clean up the inputs/outputs on VIP.
B. Additional features for avanced use:
    B.1 Display session properties to the user
    B.2 Clone a session to avoid uploading the same dataset twice

Background Specifications:
C. A VIP session should persist in time:
    C.1 Session attributes are backed up at each session step
    C.2 A backup can be resumed at instanciation
D. A VIP session should be user-friendly:
    D.1 Hide VIP paths to the user and allow multi-OS use (Unix, Windows)
    D.2 Prevent common mistakes in session / pipeline settings
    D.3 Interpret common API exceptions ("Error 8000", etc.)
"""

class VipLauncher():
    """
    Python class to run VIP pipelines on datasets on VIP servers.

    1 "session" allows to run 1 pipeline on 1 dataset with 1 parameter set (any number of pipeline runs).
    Minimal inputs:
    - `pipeline_id` (str) Name of the pipeline in VIP nomenclature. 
        Usually in format : *application_name*/*version*.
    - `input_settings` (dict) All parameters needed to run the pipeline.
        See pipeline description.

    N.B.: all instance methods require that `VipLauncher.init()` has been called with a valid API key. 
    See GitHub documentation to get your own VIP API key.
    """

                    ##################
    ################ Class Attributes ##################
                    ##################

    # Default prefix for unnamed sessions
    _NAME_PREFIX = "session_"
    # List of pipelines available to the user
    _PIPELINES = []
    # Main properties for this class
    _PROPERTIES = [
        "session_name", 
        "pipeline_id", 
        "result_dir", 
        "input_settings", 
        "workflows"
    ]

                    #################
    ################ Main Properties ##################
                    ################# 

    # Session Name
    @property
    def session_name(self) -> str:
        """A unique name to identify this session."""
        return self._session_name
    
    @session_name.setter
    def session_name(self, name: str) -> None:
        """Set the session name."""
        # Check for conflict with instance attributes
        if self._is_defined("_session_name") and (name != self._session_name):
            raise ValueError(f"Session name cannot be changed ('{self._session_name}' -> '{name}').")
        # Check the name
        self._check_session_name(name=name)
        # Assign
        self._session_name = name

    @session_name.deleter
    def session_name(self) -> None:
        """Delete the input settings"""
        del self._session_name
    # -------------------------------
    # ------------------------------------------------

    # Pipeline identifier
    @property
    def pipeline_id(self) -> str:
        """Name of the pipeline in VIP."""
        return self._pipeline_id
    
    @pipeline_id.setter
    def pipeline_id(self, pId: str) -> None:
        """Set the pipeline identifier"""
        # Check for conflict with instance attributes
        if self._is_defined("_pipeline_id") and (pId != self._pipeline_id):
            raise ValueError(f"Pipeline identifier cannot be changed for session: {self._session_name} ('{self._pipeline_id}' -> '{pId}').")
        # Check the pipeline ID (if possible)
        self._check_pipeline_id(pipeline_id=pId)
        # Assign
        self._pipeline_id = pId

    @pipeline_id.deleter
    def pipeline_id(self) -> None:
        """Delete the pipeline identifier"""
        del self._pipeline_id
    # ------------------------------------------------

    # Input settings
    @property
    def input_settings(self) -> dict:
        """All parameters needed to run the pipeline."""
        return self._input_settings
    
    @input_settings.setter
    def input_settings(self, new_settings: dict):
        """Set the input settings."""
        # Check for conflict with instance attributes
        if self._is_defined("_input_settings") and (new_settings != self._input_settings):
            raise ValueError(f"Input settings cannot be changed for session: {self.session_name}.")
        # Assign
        self._input_settings = new_settings

    @input_settings.deleter
    def input_settings(self) -> None:
        """Delete the input settings"""
        del self._input_settings
    # ------------------------------------------------

    # Output directory
    @property
    def result_dir(self) -> str:
        """Path to the VIP directory where pipeline outputs will be stored."""
        return str(self._result_dir)
    
    @result_dir.setter
    def result_dir(self, new_dir: str) -> None:
        """Set the result directory"""
        # Check for conflict with instance attributes
        if self._is_defined("_result_dir") and (new_dir != self._result_dir):
            raise ValueError(f"Results directory cannot be changed for session: {self.session_name} ('{self._result_dir}' -> '{new_dir}').")
        # Assign
        self._result_dir = PurePosixPath(new_dir)

    @result_dir.deleter
    def result_dir(self) -> None:
        """Delete the result directory"""
        del self._result_dir
    # ------------------------------------------------

    # Workflows
    @property
    def workflows(self) -> dict:
        """Workflows inventory"""
        return self._workflows
    
    @workflows.setter
    def workflows(self, workflows: dict) -> None:
        # Check conflicts with instance value
        if self._is_defined("_workflows") and (workflows != self.workflows):
            raise ValueError(f"Workflows inventory cannot be changed for session: {self.session_name}.")
        # Assign
        self._workflows = workflows

    @workflows.deleter
    def workflows(self) -> None:
        del self._workflows
    # ------------------------------------------------

                    #############
    ################ Constructor ##################
                    #############

    def __init__(
            self, session_name="", pipeline_id="",  
            input_settings:dict={}, result_dir="", verbose=True
        ) -> None:
        """
        Create a VipLauncher instance from keyword arguments. 
        Displays informations if `verbose` is True.

        Available keywords:
        - `session_name` (str) A name to identify this session.
            Default value: 'session_[date]_[time]'

        - `pipeline_id` (str) Name of your pipeline in VIP. 
            Usually in format : *application_name*/*version*.

        - `input_settings` (dict) All parameters needed to run the pipeline.
            See pipeline description for more information.

        - `result_dir` (str) Path to the VIP directory where pipeline outputs will be stored.
        """
        # Session Name
        self.session_name = (
            session_name if session_name
            # default value
            else self._NAME_PREFIX + time.strftime("%y%m%d_%H%M%S", time.localtime())
        )
        # Pipeline identifier
        if pipeline_id:
            self.pipeline_id = pipeline_id
        # Input settings
        if input_settings:
            self.input_settings = input_settings 
        # Output directory
        if result_dir :
            self.result_dir = result_dir
        # Workflows inventory
        self._workflows = {}
        # End
        if verbose:
            print(f"\n<<< SESSION '{self.session_name}' >>>\n")
    # ------------------------------------------------

                    ################
    ################ Public Methods ##################
                    ################

    #################################################
    # ($A) Manage a session from start to finish
    #################################################

    # ($A.1) Login to VIP
    @classmethod
    def init(cls, api_key: str, verbose=True, **kwargs) -> VipLauncher:
        """
        Handshakes with VIP using your API key. 
        Prints a list of pipelines available with the API key, unless `verbose` is False.
        Returns a VipLauncher instance which properties can be provided as keyword arguments (`kwargs`).

        Input `api_key` can be either:
        A. (unsafe) a string litteral containing your API key, or
        B. (safer) a path to some local file containing your API key, or
        C. (safer) the name of some environment variable containing your API key.

        In cases B or C, the API key will be loaded from the local file or the environment variable.        
        """
        # Check if `api_key` is in a local file or environment variable
        if os.path.exists(api_key): # local file
            with open(api_key, "r") as kfile:
                true_key = kfile.read().strip()
        elif api_key in os.environ: # environment variable
            true_key = os.environ[api_key]
        else: # string litteral
            true_key = api_key
        # Set User API key
        try:
            # setApiKey() may return False
            assert vip.setApiKey(true_key), \
                f"(!) Unable to set the VIP API key: {true_key}.\nPlease check the key or retry later."
        except RuntimeError as vip_error:
            # setApiKey() may throw RuntimeError in case of bad key
            print(f"(!) Unable to set the VIP API key: {true_key}.\n    Original error message:")
            raise vip_error
        except(json.decoder.JSONDecodeError) as json_error:
            # setApiKey() may throw JSONDecodeError in special cases
            print(f"(!) Unable to set the VIP API key: {true_key}.\n    Original error message:")
            raise json_error
        # Update the list of available pipelines
        try:
            cls._get_available_pipelines()
            # RunTimeError is handled downstream
        except(json.decoder.JSONDecodeError) as json_error:
            # The user still cannot communicate with VIP
            print(f"(!) Unable to communicate with VIP. Check the API key:\n\t{true_key}")
            print(f"    Original error messsage:")
            raise json_error
        # Double check user can access pipelines
        assert cls._PIPELINES, f"Your API key does not allow you to execute pipelines on VIP. \n\tAPI key: {true_key}"
        if verbose:
            print("\nYou are communicating with VIP.\nAvailable pipelines:")
            print(*cls._PIPELINES, sep=", ")
        # Return a VipLauncher instance for method cascading
        return VipLauncher(verbose=(verbose and kwargs), **kwargs)
    # ------------------------------------------------
   
    # ($A.3) Launch executions on VIP 
    def launch_pipeline(
            self, pipeline_id="", input_settings:dict={}, result_dir="", nb_runs=1, verbose=True
        ) -> VipLauncher:
        """
        Launches pipeline executions on VIP.

        Input parameters :
        - `pipeline_id` (str) The name of your pipeline in VIP.
        - `input_settings` (dict) All parameters needed to run the pipeline.
        - `result_dir` (str) Path to the VIP folder where execution results will be stored.
        - `nb_runs` (int) Number of parallel runs of the same pipeline with the same settings.
        - Set `verbose` to False to run silently.
        
        Default behaviour:
        - Raises TypeError if inputs are missing
        - Raises ValueError in case of conflict with previous inputs
        - Raises RuntimeError in case of failure on VIP servers.
        """
        if verbose: print("\n<<< LAUNCH PIPELINE >>>\n")
        # Parameter checks
        if verbose: print("Parameters checks")
        # Check & Update the pipeline identifier
        if verbose: print("\tPipeline identifier: ", end="")
        if pipeline_id:
            self.pipeline_id = pipeline_id
        if not self._check_pipeline_id():
            raise TypeError("(!) Pipeline identifier could not be checked without call to init().")
        if verbose: print("OK.")
        # Update the result directory
        if verbose: print("\tOutput directory: ", end="")
        if result_dir: 
            self.result_dir=result_dir
        # Check existence
        if not self._is_defined("_result_dir"):
            raise TypeError("Please provide an result directory for Session: %s" %self.session_name)
        # Ensure the directory exists
        if self._make_dir(path=self._result_dir, location="vip"):
            print("Created on VIP.")
        else:
            print("OK.")
        # Update the input parameters
        if input_settings:
            self.input_settings = input_settings
        if verbose: print("\tInput settings: ", end="")
        # Check existence
        if not self._is_defined("_input_settings"):
            raise TypeError("Please provide input parameters for Session: %s" %self.session_name)  
        # Check content
        try:
            if not self._check_input_settings(location="vip"):
                raise TypeError("Input settings could not be checked.")
        except RuntimeError as handled_error:
            # this may throw a RuntimeError (handled upstream)
            # if pipeline definition could not be loaded from VIP 
            if verbose: print("\n(!) Input settings could not be checked.")
            raise handled_error from None
        if verbose: print("OK.")
        # End of parameters checks
        if verbose: print()
        # Display the launch
        if verbose:
            print("Launching %d new execution(s) on VIP" % nb_runs)
            print("-------------------------------------")
            print("\tSession Name:", self.session_name)
            print("\tPipeline Identifier:", self.pipeline_id)
            print("\tStarted Workflows:", end="\n\t\t")
        # Launch all executions in parallel
        for nEx in range(nb_runs):
            try:
                # This part may fail for a number of reasons
                workflow_id = self._init_exec()
            except RuntimeError as vip_error:
                print("\n-------------------------------------")
                print(f"(!) Stopped after {nEx} execution(s).")
                self._handle_vip_error(vip_error)
            # Display
            if verbose: print(workflow_id, end=", ")
            # Update the workflow inventory
            try: self._workflows[workflow_id] = self._get_exec_infos(workflow_id)
            except RuntimeError as vip_error: self._handle_vip_error(vip_error)
        # Display success
        if verbose: 
            print("\n-------------------------------------")
            print("Done.")
        # Return for method cascading
        return self
    # ------------------------------------------------

    # ($A.4) Monitor worflow executions on VIP 
    def monitor_workflows(self, waiting_time=30, verbose=True) -> VipLauncher:
        """
        Updates and displays status for each execution launched in the current session.
        - If an execution is still running, updates status every `waiting_time` (seconds) until all runs are done.
        - If `verbose`is True, displays a full report when all executions are done.
        """
        if verbose: print("\n<<< MONITOR WORKFLOW >>>\n")
        # Check if current session has existing workflows
        if not self._workflows:
            if verbose:
                print("\nThis session has not yet launched any execution.")
                print("Run launch_pipeline() to launch workflows on VIP.")
            return self
        # Update existing workflows
        if verbose: print("Updating worflow inventory ... ", end="")
        self._update_workflows()
        if verbose: print("Done.")
        # Check if workflows are still running
        if self._still_running():
            # First execution report
            self._execution_report(verbose)
            # Display standby
            if verbose:
                print("\n-------------------------------------------------------------")
                print("The current proccess will wait until all executions are over.")
                print("Their progress can be monitored on the VIP portal:")
                print("\thttps://vip.creatis.insa-lyon.fr/")
                print("-------------------------------------------------------------")
            # Standby until all executions are over
            while self._still_running():
                time.sleep(waiting_time)
                self._update_workflows()
            # Display the end of executions
            if verbose: print("All executions are over.")
        # Last execution report
        self._execution_report(verbose)
        # Return for method cascading
        return self
    # ------------------------------------------------

    # ($A.6) Clean session data on VIP
    def finish(self, timeout=300, verbose=True) -> VipLauncher:
        """
        - This process waits for effective data deletion until `timeout` (seconds) is reached.
        - Displays information if `verbose` is True.
        """
        # Initial display
        if verbose: print("\n<<< FINISH >>>\n")
        # Check if workflows are still running (without call to VIP)
        if self._still_running():
            # Update the workflow inventory
            if verbose: print("Updating worflow inventory ... ", end="")
            self._update_workflows()
            if verbose: print("Done.")
            # Return is workflows are still running
            if self._still_running():
                self._execution_report(verbose)
                if verbose: 
                    print("\n(!) This session cannot be finished since the pipeline might still generate data.\n")
                    return self
        # Initial display
        if verbose:
            print("Ending Session:", self.session_name)
            print("Removing session data")
            print("---------------------")
        # Browse paths to delete
        success = True
        for path, location in self._path_to_delete().items():
            # Display progression
            if verbose: print(f"[{location}] {path} ... ", end="")
            # Check data existence
            if not self._exists(path, location):
                # Session may be already over
                if verbose: print("Already removed.")
            else:
                # Erase the path
                done = self._delete_and_check(
                    path=path, location=location, timeout=timeout
                    )
                # Display 
                if verbose: 
                    if done:
                        print("Done.")
                    else:
                        print(f"\n\t(!) Timeout reached ({timeout} seconds).\n")
                # Update success
                success = success and done
        # End of loop
        if verbose: 
            print("-------------------------\n")
            print("Updating workflows status")
            print("-------------------------")
        # Set the workflow status to "removed" to avoid dead links in future downloads
        removed_outputs = True
        for wid in self._workflows:
            if verbose: print(f"{wid}: ", end="")
            if not ( 
                # The output list is not empty
                self._workflows[wid]["outputs"] 
                # The workflow directory still exists
                and self._exists(PurePosixPath(self._workflows[wid]["outputs"][0]["path"]).parent, location="vip")
                ):
                self._workflows[wid]["status"] = "Removed"
                if verbose: print("Removed.")
            else:
                # Not all workflows were removed
                removed_outputs = False
                if verbose: print("")
        # Last display
        if verbose:
            print("-------------------------")
            if removed_outputs:
                print(f"Session <{self.session_name}> is over.\n")
            else:
                print(f"Session <{self.session_name}> is not over yet.")
                print("Run finish() again later to end the process.\n")
        # Return for method cascading
        return self
    # ------------------------------------------------


    ###########################################
    # ($B) Additional Features for Advanced Use
    ###########################################

    # ($B.1) Display session properties in their current state
    def display_properties(self) -> VipLauncher:
        """
        Displays useful properties in JSON format.
        - `session_name` : current session name
        - `pipeline_id`: pipeline identifier
        - `result_dir` : path to the pipeline outputs *in your VIP Home directory*
        - `input_settings` : input parameters sent to VIP 
        (note that file locations are bound to `vip_input_dir`).
        - `workflows`: workflow inventory, identifying all pipeline runs in this session.
        """
        # Get properties
        session_data = {
            prop: getattr(self, prop) for prop in self._PROPERTIES
        }
        # Display
        print(json.dumps(session_data, indent=4))
        # Return for method cascading
        return self
    # ------------------------------------------------

                    #################
    ################ Private Methods ################
                    #################

    # Method to check existence of a distant resource.
    @classmethod
    def _exists(cls, path, location="vip") -> bool:
        """
        Checks existence of a distant resource (`location`="vip").
        `path` can be a string or Pathlib object.
        """
        # Check `location`
        if location != "vip":
            raise NotImplementedError(f"Unknown location: {location}")
        # Check path existence
        try: 
            return vip.exists(str(path))
        except RuntimeError as vip_error:
            cls._handle_vip_error(vip_error)
    # ------------------------------------------------
    
    # Method to create a distant directory
    @classmethod
    def _create_dir(cls, path, location="vip") -> None:
        """
        Creates a directory at `path`, on VIP servers if `location` is "vip".

        `path`can be a string or PathLib object.
        Returns the VIP path of the newly created folder.
        """
        # Check `location`
        if location != "vip": 
            raise NotImplementedError(f"Unknown location: {location}")
        # Create directory
        try: 
            if not vip.create_dir(str(path)):
                msg = f"The following directoy could not be created on VIP:\n\t{path}\n"
                msg += "Please retry later. Contact VIP support (vip-support@creatis.insa-lyon.fr) if this cannot be fixed."
                raise AssertionError(msg)
        except RuntimeError as vip_error:
            cls._handle_vip_error(vip_error)    
            
    # ------------------------------------------------

    # Method to create a directory leaf on the top of any VIP path
    @classmethod
    def _make_dir(cls, path: PurePath, location: str, **kwargs) -> str:
        """
        Creates each non-existent directory in `path` (like pathlib.Path.mkdir()), 
        in the storage facility designed by `location`.
        - Directories are created using: cls._create_dir(`path`, `location`, **`kwargs`)
        - Existence is checked using: cls._exists(`path`, `location`).

        Returns the newly created part of `path` (empty string if `path` already exists).
        """
        # Case : the current path exists
        if cls._exists(path=path, location=location) :
            return ""
        # Find the 1rst non-existent node in the arborescence
        first_node = path
        while not cls._exists(first_node.parent, location=location):
            first_node = first_node.parent
        # Create the first node 
        cls._create_dir(path=first_node, location=location, **kwargs)
        # Make the other nodes one by one
        dir_to_make = first_node
        while dir_to_make != path:
            # Find the next directory to make
            dir_to_make /= path.relative_to(dir_to_make).parts[0]
            # Make the directory
            cls._create_dir(path=dir_to_make, location=location, **kwargs)
        # Return the created nodes
        return str(path.relative_to(first_node.parent))
    # ------------------------------------------------

    # (A.3) Launch pipeline executions on VIP servers
    ##################################################
    def _init_exec(
            self, pipeline_id="", session_name="", input_settings="",
            result_dir="") -> str:
        """
        Initiates one VIP workflow with `pipeline_id`, `session_name`, `input_settings`, `result_dir`.
        Returns the workflow identifier.
        """
        # Parse arguments
        if not pipeline_id:
            pipeline_id = self.pipeline_id
        if not session_name:
            session_name = self.session_name
        if not input_settings:
            input_settings = self.input_settings
        if not result_dir:
            result_dir = self.result_dir
        # Launch execution
        return vip.init_exec(
            pipeline = pipeline_id, 
            name = session_name, 
            inputValues = input_settings,
            resultsLocation = result_dir
        )
    # ------------------------------------------------

    # (A.4) Monitor pipeline executions on VIP servers
    ##################################################

    # Get and display a report over all executions in the current session
    def _execution_report(self, verbose=True) -> dict:
        """
        Sorts workflows by status. Returns the result in dictionnary shape.
        If `verbose` is True, interprets the result to the user.
        """
        # Initiate status report
        report={}
        # Browse workflows
        for wid in self._workflows:
            # Get status
            status = self._workflows[wid]["status"]
            # Update the report
            if status in report:
                # update status
                report[status].append(wid)
            else:
                # create status
                report[status] = [wid]
        # Interpret the report to the user
        if verbose:
            # Function to print a detailed worfklow list
            def detail(worfklows: list): 
                for wid in worfklows:
                    print("\t", wid, ", started on:", self._workflows[wid]["start"])
            # Browse status
            for status in report:
                # Display running executions
                if status == 'Running':
                    # check if every workflow is running
                    if len(report[status])==len(self._workflows):
                        print(f"All executions are currently running on VIP.")
                    else: # show details
                        print(f"{len(report[status])} execution(s) is/are currently running on VIP:")
                        detail(report[status])
                # Display successful executions
                elif status == 'Finished':
                    # check if every run was successful
                    if len(report[status])==len(self._workflows):
                        print(f"All executions ({len(report[status])}) ended with success.")
                    else: # show details
                        print(f"{len(report[status])} execution(s) ended with success:")
                        detail(report[status])
                # Display executions with removed data
                elif status == 'Removed':
                    # check if every run was removed
                    if len(report[status])==len(self._workflows):
                        print("This session is over.")
                        print("All output data were removed from VIP servers.")
                    else: # show details
                        print(f"Outputs from {len(report[status])} execution(s) were removed from VIP servers:")
                        detail(report[status])
                # Display failed executions
                else:
                    # check if every run had the same cause of failure:
                    if len(report[status])==len(self._workflows):
                        print(f"All executions ({len(report[status])}) ended with status:", status)
                    else: # show details
                        print(f"{len(report[status])} execution(s) ended with status:", status)
                        detail(report[status])
            # End of loop on report
        # Return the report
        return report
    # ------------------------------------------------

    def _still_running(self) -> int:
        """
        Returns the number of workflows which are still running on VIP.
        (!) Requires prior call to self._update_workflows to avoid unnecessary connexions to VIP
        """
        # Workflow count
        count = 0
        for wid in self._workflows:
            # Update count
            count += int(self._workflows[wid]["status"]=="Running")
        # Return count
        return count   
    # ------------------------------------------------

    # Update all worflow information at once
    def _update_workflows(self) -> None:
        """
        Updates the status of each workflow in the inventory. 
        """
        for wid in self._workflows:
            # Check if workflow data have been removed
            if self._workflows[wid]["status"] != "Removed":
                # Recall execution info & update the workflow status
                self._workflows[wid].update(self._get_exec_infos(wid))
    # ------------------------------------------------

    # Method to get useful information about a given workflow
    @classmethod
    def _get_exec_infos(cls, workflow_id: str) -> dict:
        """
        Returns succint information on `workflow_id`:
        - Execution status (VIP notations)
        - Starting time (local time, format '%Y/%m/%d %H:%M:%S')
        - List of paths to the output files.
        """
        try :
            # Get execution infos
            infos = vip.execution_info(workflow_id)
            # Secure way to get execution results
            files = vip.get_exec_results(workflow_id)
        except RuntimeError as vip_error:
            cls._handle_vip_error(vip_error)
        # Return filtered information
        return {
            # Execution status (VIP notations)
            "status": infos["status"],
            # Starting time (human readable)
            "start": time.strftime(
                '%Y/%m/%d %H:%M:%S', time.localtime(infos["startDate"]/1000)
                ),
            # Returned files (filtered information)
            "outputs": [
                {
                    key: elem[key] 
                    for key in ["path", "isDirectory", "size", "mimeType"]
                    if key in elem
                }
                for elem in files
            ]
        }
    # ------------------------------------------------

    # Path to delete during session finish
    def _path_to_delete(self) -> dict:
        """Returns the folders to delete during session finish, with appropriate location."""
        return {
            self._result_dir: "vip"
        }
    
    # ------------------------------------------------
   
    # Function to delete a path
    @classmethod
    def _delete_path(cls, path: PurePath, location="vip") -> None:
        # Check `location`
        if location != "vip":
            raise NotImplementedError(f"Unknown location: {location}")
        done = vip.delete_path(str(path))
        if not done:
            # Errors are handled by returning False in `vip.delete_path()`
            msg = f"\n'{path}' could not be removed from VIP servers.\n"
            msg += "Check your connection with VIP and path existence on the VIP portal.\n"
            raise RuntimeError(msg)

    # Function to delete a path on VIP with warning
    @classmethod
    def _delete_and_check(cls, path: PurePath, location="vip", timeout=300) -> bool:
        """
        Deletes `path` on `location` and waits until `path` is actually removed.
        After `timeout` (seconds), displays a warning if `path` still exist.
        """
        # Delete the path
        cls._delete_path(path, location)
        # Standby until path is indeed removed (give up after some time)
        start = time.time()
        timeout = 300 # max time in seconds
        t = time.time() - start
        while (t < timeout) and cls._exists(path, location):
            time.sleep(2)
            t = time.time() - start
        # Check if the data have indeed been removed
        return (t >= timeout)

    # ($D.2) Prevent common mistakes in session / pipeline settings 
    ###############################################################

    # Check if an attribute has been correctly defined
    def _is_defined(self, var) -> bool :
        """Returns True if `var` has already been set by the user, False otherwise."""
        return var in self.__dict__

    # Check the session name to avoid name errors in VIP
    def _check_session_name(self, name="") -> None:
        """
        Session name characters must be only aphanumeric or hyphens.
        Raises ValueError otherwise.
        """
        # Input
        if not name:
            name = self._session_name
        # Green Flag
        ok_name = True
        # Criterion
        for letter in name:
            ok_name &= letter.isalnum() or (letter in "_- ")
        # Error message
        if not ok_name:
            raise ValueError("Session name must contain only alphanumeric characters, spaces and hyphens: '-', '_'")
    # ------------------------------------------------    

    # Check the pipeline identifier based on the list of available pipelines
    def _check_pipeline_id(self, pipeline_id: str="") -> bool:
        """
        Checks if the pipeline identifier `pipeline_id` is available for this session.
        Raises ValueError otherwise.
        If `pipeline_id` is not provided, checks instance attribute.
        (!) Requires prior call to VipLauncher.init() to avoid useless connexion. Returns False otherwise.
        """
        # Default value
        if not pipeline_id:
            if not self._is_defined("_pipeline_id"):
                raise AttributeError("Please provide a pipeline identifier for Session: %s" %self.session_name)
            pipeline_id = self._pipeline_id
        # Available pipelines
        if not self._PIPELINES:
            return False
        # Check pipeline identifier
        if  pipeline_id not in self._PIPELINES:
            raise ValueError(f"Please provide a valid pipeline identifier. Available pipelines :\n{', '.join(self._PIPELINES)}\n")
        # Return
        return True
    # ------------------------------------------------

    # Function that lists available pipeline identifiers for a given VIP accout
    @classmethod
    def _get_available_pipelines(cls) -> list:
        """
        Updates the list of available pipelines (`cls._PIPELINES`) for current VIP account 
        (defined by user API key). Returns the same list.
        """
        try:
            all_pipelines = vip.list_pipeline()
        except RuntimeError as vip_error:
            cls._handle_vip_error(vip_error)
        cls._PIPELINES = [ 
            pipeline["identifier"] for pipeline in all_pipelines 
            if pipeline["canExecute"] is True 
        ]
        return cls._PIPELINES
    # ------------------------------------------------

    # Check the input settings based on the pipeline descriptor
    def _check_input_settings(self, input_settings: dict={}, location="", verbose=True) -> bool:
        """
        Checks `input_settings` with respect to pipeline descriptor. 
        
        `location` refers to the storage infrastructure where input files should be found (e.g., VIP).
        Use the same nomenclature as defined in self._exists() (e.g., `location="vip"`).
        
        Detailed output:
            - Prints warnings if `verbose` is True.
            - Returns True if the input settings and pipeline descriptor were found, False otherwise.
            - Raises TypeError if some input parameter is missing.
            - Raises ValueError if some input value does not the fit with the pipeline descriptor.
            - Raises FileNotFoundError some input file does not exist. 
            - Raises RuntimeError if communication failed with VIP servers.
        """
        # Check arguments & instance properties
        if not input_settings:
            if self._is_defined("_input_settings"):
                input_settings = self._input_settings
            else:
                if verbose: print("(!) No input settings to check")
                return False
        # Check the pipeline identifier
        if not self._is_defined("_pipeline_id"): 
            if verbose: print("(!) Input settings could not be checked without a pipeline identifier.")
            return False
        # Get the true pipeline parameters
        try :            
            pipeline_def = vip.pipeline_def(self._pipeline_id)["parameters"]
        except RuntimeError as vip_error:
            self._handle_vip_error(vip_error)
        # Parameter names
        self._check_input_keys(input_settings, pipeline_def, verbose=verbose)
        # Parameter values
        self._check_input_values(input_settings, pipeline_def, location=location)
        # Return True when all checks are complete
        return True
    # ------------------------------------------------      
    
    # Check the parameter names according to pipeline descriptor
    def _check_input_keys(self, input_settings: dict, pipeline_def: dict, verbose=True) -> None:
        """
        Looks for mismatches in keys between `input_settings` and `pipeline_def`.
        """
        # Check every required field is there 
        missing_fields = (
            # pipeline parameters
            {param["name"] for param in pipeline_def 
                if not param["isOptional"] and (param["defaultValue"] == "$input.getDefaultValue()")} 
            # current parameters
            - set(input_settings.keys()) 
        )
        # Raise an error if a field is missing
        if missing_fields:
            raise TypeError("Missing input parameter(s) :\n" + ", ".join(missing_fields))
        # Check every input parameter is a valid field
        unknown_fields = (
            set(input_settings.keys()) # current parameters
            - {param["name"] for param in pipeline_def} # pipeline parameters
        )
        # Display a warning in case of useless inputs
        if unknown_fields and verbose:
            print("(!) The following input parameters: " + ", ".join(unknown_fields) \
             + f"\n    are useless for the pipeline ('{self._pipeline_id}'). This may throw RuntimeError later.")
    # ------------------------------------------------
    
    # Check the parameter values according to pipeline descriptor
    def _check_input_values(self, input_settings: dict, pipeline_def: dict, location="") -> None:
        """
        Checks if each parameter value in `input_settings` matches its pipeline description in `parameters`.
        `location` refers to the storage infrastructure (e.g., VIP) to scan for missing files.
        """
        # Browse the input parameters
        for param in pipeline_def:
            # Get parameter name
            name = param['name']
            # Skip irrelevant inputs (this should not happen after self._check_input_keys())
            if name not in input_settings:
                continue
            # Get input value
            value = input_settings[name]
            # Check string format
            if (param["type"] == "String") and not self._is_input_string(value):
                raise ValueError(f"Parameter '{name}' should be a string or a list of strings.")
            # Check files existence
            elif param["type"] == "File":
                # Check string format
                if not self._is_input_string(value):
                    raise ValueError(f"Parameter '{name}' should be a string or a list of strings.")
                # Ensure every file exists if `location` was provided in self._check_input_settings()
                if location:
                    missing_file = self._missing_input_file(value, location)
                    if missing_file:
                        raise FileNotFoundError(f"File: '{missing_file}' does not exist.")
            # Check other input formats ?
            else: 
                # TODO
                pass
        # ------------------------------------------------
        
    # Function to assert the input is a string
    @staticmethod
    def _is_input_string(value) -> bool: 
        """
        Returns True if `value` is either a string or a list of strings.
        """
        if isinstance(value, list):
            return all([isinstance(v, str) for v in value])
        else:
            return isinstance(value, str)
    
    # Function to assert file existence
    @classmethod
    def _missing_input_file(cls, value, location: str) -> str: 
        """
        Returns the path the first non-existent file in `value` (or an empty string by default).
        `value` can contain a single file path or a list of paths.
        `location` refers to the storage infrastructure (e.g., "vip") to feed in cls._exists().
        """
        # Case : list of files
        if isinstance(value, list):
            for file in value : 
                if not cls._exists(path=file, location=location):
                    return file
            return ""
        # Case: single file
        else:
            return "" if cls._exists(path=value, location=location) else value

    # ($D.3) Interpret common API exceptions
    ########################################

    # Function to handle VIP runtime errors and provide interpretation to the user
    # TODO add the following use cases:
        # - Connection to VIP expired during workflow monitoring
        # - "Error 8000": better interpretation
    @staticmethod
    def _handle_vip_error(vip_error: RuntimeError) -> None:
        """
        Rethrows a RuntimeError `vip_error` which occured in the VIP API,
        with interpretation depending on the error code.
        """
        # Enumerate error cases
        message = vip_error.args[0]
        if message.startswith("Error 8002") or message.startswith("Error 8003") \
            or message.startswith("Error 8004"):
            # "Bad credentials"  / "Full authentication required" / "Authentication error"
            interpret = (
                f"Could not communicate with VIP.\n\t'{message}'"
                + "\nRun VipLauncher.init() with a valid API key to handshake with VIP servers."
            )
        elif message.startswith("Error 8000"):
            #  Probably wrong values were fed in `vip.init_exec()`
            interpret = (
                f"\n\t'{message}'"
                + "\nPlease carefully check that session_name / pipeline_id / input_parameters "
                + "are valid and do not contain any forbidden character."
                + "\nIf this cannot be fixed, contact VIP support (vip-support@creatis.insa-lyon.fr)."
            )
        elif message.startswith("Error 2000") or message.startswith("Error 2001"):
            #  Maximum number of executions
            interpret = (
                f"\n\t'{message}'"
                + "\nPlease wait until current executions are over, "
                + "or contact VIP support (vip-support@creatis.insa-lyon.fr) to increase this limit."
            )
        else:
            # Unhandled runtime error
            interpret=(
                f"\n\t{message}"
                + "\nIf this cannot be fixed, contact VIP support (vip-support@creatis.insa-lyon.fr)."
            )
        # Display the error message
        raise RuntimeError(interpret) from None
    # ------------------------------------------------

#######################################################

if __name__=="__main__":
    pass