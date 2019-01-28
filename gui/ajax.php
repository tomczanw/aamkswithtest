<?php
session_name('aamks');
require_once("inc.php"); 

function ajaxChangeActiveScenario() { #{{{
	$r=$_SESSION['nn']->query("SELECT u.email,s.project_id,s.id AS scenario_id,s.scenario_name, u.active_editor, u.user_photo, u.user_name, p.project_name FROM scenarios s JOIN projects p ON s.project_id=p.id JOIN users u ON p.user_id=u.id WHERE s.id=$1 AND p.user_id=$2",array($_POST['ch_scenario'], $_SESSION['main']['user_id']));
	$_SESSION['nn']->ch_main_vars($r[0]);
	echo json_encode(array("msg"=>"", "err"=>0, "data"=>$_SESSION['main']['scenario_name']));
}
/*}}}*/
function ajaxLaunchSimulation() { #{{{
	$aamks=getenv("AAMKS_PATH");
	$scenario=$_SESSION['main']['working_home'];
	$cmd="cd $aamks; python3 aamks.py $scenario"; 

	$z=shell_exec("$cmd");
	// TODO: python should return errors on fatal

	if(!empty($z)) { 
		echo json_encode(array("msg"=>"ajaxLaunchSimulation(): OK", "err"=>0, "data"=>$z));
	} else {
		echo json_encode(array("msg"=>"ajaxLaunchSimulation(): $z", "err"=>1, "data"=>''));
	}
}
/*}}}*/
function ajaxMenuContent() { /*{{{*/
	# psql aamks -c "select p.*,s.* from scenarios s LEFT JOIN projects p ON s.project_id=p.id WHERE user_id=1"
	# psql aamks -c "select * from scenarios"
	# psql aamks -c "select * from projects"

	$r=$_SESSION['nn']->query("SELECT s.* FROM scenarios s LEFT JOIN projects p ON s.project_id=p.id WHERE user_id=$1 ORDER BY modified DESC", array($_SESSION['main']['user_id']));
	$form='';
	$form.="<close-left-menu-box><img src=/aamks/css/close.svg></close-left-menu-box><br>";
	$form.="<a class=blink href=/aamks/projects.php?projects_list>Home</a><br>";
	$form.="<a id=launch_simulation class=blink>Launch</a><br>";
	$form.="<a class=blink target=_blank href=/aamks/apainter/index.php>Apainter</a><br>";
	$form.="<a class=blink target=_blank href=/aamks/animator/index.php>Animator</a><br>";
	$form.="<br>";
	$form.="Scenario<br><select id='choose_scenario'>\n";
	$form.="<option value=".$_SESSION['main']['scenario_id'].">".$_SESSION['main']['scenario_name']."</option>\n";
	foreach($r as $k=>$v) {
		$form.="<option value='$v[id]'>$v[scenario_name]</option>\n";
	}
	$form.="</select>\n";
	echo json_encode(array("msg"=>"", "err"=>0,  "data"=> $form));
}
/*}}}*/
function ajaxAnimsList() { /*{{{*/
	$f=$_SESSION['main']['working_home']."/workers/anims.json";
	if(is_file($f)) { 
		$data=json_decode(file_get_contents($f));
		echo json_encode(array("msg"=>"ajaxAnimsList(): OK", "err"=>0,  "data"=> $data));
	} else {
		echo json_encode(array("msg"=>"ajaxAnimsList(): $z", "err"=>1, "data"=>''));
	}
}
/*}}}*/
function ajaxAnimsStatic() { /*{{{*/
	$f=$_SESSION['main']['working_home']."/workers/static.json";
	if(is_file($f)) { 
		$data=json_decode(file_get_contents($f));
		echo json_encode(array("msg"=>"ajaxAnimsStatic(): OK", "err"=>0,  "data"=> $data));
	} else {
		echo json_encode(array("msg"=>"ajaxAnimsStatic(): $z", "err"=>1, "data"=>''));
	}
}
/*}}}*/
function ajaxSingleAnim() { /*{{{*/
	if($_POST['unzip']=='funUpDown') { 
		ajaxSingleAnimFunUpDown();
	} else if($_POST['unzip']=='funCircle') { 
		ajaxSingleAnimFunCircle();
	} else { 
		$f=$_SESSION['main']['working_home']."/workers/$_POST[unzip]";
		if(is_file($f)) { 
			$z=json_decode(shell_exec("unzip -qq -c $f anim.json"));
		}
		if(!empty($z)) { 
			echo json_encode(array("msg"=>"ajaxSingleAnim(): OK", "err"=>0, "data"=>$z));
		} else {
			echo json_encode(array("msg"=>"ajaxSingleAnim(): $z", "err"=>1, "data"=>''));
		}
	}
}
/*}}}*/
function ajaxSingleAnimFunCircle() { /*{{{*/
	$arr=[];
	$colors=["H", "M", "L", "N"];
	for($t=0; $t<15; $t+=2.5) { 
		$record=[];
		for($a=0; $a<19; $a++) { 
			$record[]=[ 2450 + round(100*cos($t+$a/3)), 1000 - round(100*sin($t+$a/3)), 0, 0, $colors[$a%4], 1 ];
			$record[]=[ 2450 + round(200*cos($t+$a/3)), 1000 + round(200*sin($t+$a/3)), 0, 0, $colors[$a%4], 1 ];
			$record[]=[ 2450 + round(300*cos($t+$a/3)), 1000 - round(300*sin($t+$a/3)), 0, 0, $colors[$a%4], 1 ];
		}
		$arr[]=$record;
	}
	$collect=[ "simulation_id" => 1, "project_name" => "demo", "simulation_time" => 200, "time_shift" => 0  ];
	$collect['data']=$arr;
	echo json_encode(array("msg"=>"ajaxSingleAnimFun(): OK", "err"=>0, "data"=>$collect));
}
/*}}}*/
function ajaxSingleAnimFunUpDown() { /*{{{*/
	$arr=[];
	$colors=["H", "M", "L", "N"];
	$y=[];
	for($t=0; $t<10; $t+=1) { 
		$record=[];
		for($a=0; $a<370; $a++) { 
			$y[$a]=rand(520,980);
			$color=floor($a/100);
			$record[]=[ 1020 + 8*$a, $y[$a], 0, 0, $colors[$color], 1 ];
			$y[$a]+=1500-2*$y[$a];
		}
		$arr[]=$record;
		#dd2($arr);
	}
	$collect=[ "simulation_id" => 1, "project_name" => "demo", "simulation_time" => 900, "time_shift" => 0  ];
	$collect['data']=$arr;
	echo json_encode(array("msg"=>"ajaxSingleAnimFun(): OK", "err"=>0, "data"=>$collect));
}
/*}}}*/
function ajaxApainterExport() { /*{{{*/
	$src=$_POST['cadfile'];
	$dest=$_SESSION['main']['working_home']."/cad.json";
	$z=file_put_contents($dest, $src);
	if($z>0) { 
		echo json_encode(array("msg"=>"ajaxApainterExport(): OK", "err"=>0, "data"=>""));
	} else { 
		echo json_encode(array("msg"=>"ajaxApainterExport(): Cannot export $dest", "err"=>1, "data"=>""));
	}
}
/*}}}*/
function ajaxApainterImport() { /*{{{*/
	// Apainter always checks if there's a file to import.
	// It's not an error if the file is missing -- it has been not yet created.

	if(is_file($_SESSION['main']['working_home']."/cad.json")) {
		$cadfile=file_get_contents($_SESSION['main']['working_home']."/cad.json");
		if(json_decode($cadfile)) { 
			echo json_encode(array("msg"=>"" , "err"=>0 , "data"=>json_decode($cadfile)));
		} else { 
			echo json_encode(array("msg"=>"ajaxApainterImport(): Broken cad.json", "err"=>1, "data"=>""));
		}
	}
}
/*}}}*/
function ajaxGoogleLogin() { /*{{{*/
	$_SESSION['google_data']=$_POST['google_data'];
	$_POST['google_data']['dnr']=0; //Do Not Reload page in JS/google_login.js
	if(isset($_SESSION['g_dnr'])){
		$_POST['google_data']['dnr']=1; //Do Not Reload page in JS/google_login.js
	}
	$_SESSION['g_dnr']=1;
	echo json_encode(array("msg"=>"ajaxGoogleLogin(): OK", "err"=>0,  "data"=>$_POST['google_data']));
	$_SESSION['g_name']=$_SESSION['google_data']['g_name'];
	$_SESSION['g_email'] =$_SESSION['google_data']['g_email'];
	$_SESSION['g_user_id']=$_SESSION['google_data']['g_user_id'];
	$_SESSION['g_picture']=$_SESSION['google_data']['g_picture'];
	$ret[0]=$_SESSION['nn']->do_google_login();
	$_SESSION['nn']->set_user_variables($ret[0]);
}
/*}}}*/
function ajaxPdf2svg() { /*{{{*/
	$src=$_FILES['file']['tmp_name'];
	$dest=$_SESSION['main']['working_home']."/out.svg";
	$z=shell_exec("pdf2svg $src $dest 2>&1");
	$svg='';
	if(empty($z)) { 
		$svg=shell_exec("cat $dest"); 
		$svg=preg_replace("/#/", "%23", $svg);
		echo json_encode(array("msg"=>"ajaxPdf2svg(): OK", "err"=>0,  "data"=>$svg));
	} else {
		echo json_encode(array("msg"=>"ajaxPdf2svg(): $z", "err"=>1, "data"=>""));
	}
}
/*}}}*/
function main() { /*{{{*/
	header('Content-type: application/json');

	if(!empty($_SESSION['main']['user_id']))         {
		if(isset($_GET['pdf2svg']))                  { ajaxPdf2svg(); }
		if(isset($_GET['exportApainter']))           { ajaxApainterExport(); }
		if(isset($_GET['importApainter']))           { ajaxApainterImport(); }
		if(isset($_GET['getAnimsList']))             { ajaxAnimsList(); }
		if(isset($_GET['getAnimsStatic']))           { ajaxAnimsStatic(); }
		if(isset($_GET['getSingleAnim']))            { ajaxSingleAnim(); }
		if(isset($_GET['ajaxMenuContent']))          { ajaxMenuContent(); }
		if(isset($_GET['ajaxLaunchSimulation']))     { ajaxLaunchSimulation(); }
		if(isset($_GET['ajaxChangeActiveScenario'])) { ajaxChangeActiveScenario(); }
	}
	if(isset($_GET['googleLogin']))    { ajaxGoogleLogin(); }
}
/*}}}*/
main();
?>
