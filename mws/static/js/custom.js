/**  LOCAL NAVIGATION CONTROLS updated code taken from sony.com **/
//this controls both the dropdowns and graphical style of the desktop navigation and the sliding panels of the mobile navigation
projectlight.localNav=(function(){
	var $openMenu,$navigation,$navContainer,$topUL,$topListItems,$allListItems,$links,$secondLevelListitems,$allMenuLists,n,$allNavLinks,menuPosition=0,m;
	return{
		init:function(u){
			$navigation = $(".campl-local-navigation");
			
			//only run if there is navigation available in the page 
			if($navigation.length > 0){
				//need to remove btn from IE7 and IE8 - feature detection for media queries
				if(Modernizr.mq('only all')){
					$navigation.prepend('<p class="campl-closed campl-menu-btn" id="menu-btn"><a href="#"><span>Menu</span> <span class="campl-menu-btn-arrow"></span></a></p>')	
					$openMenu = $("#menu-btn a");

					//bind click event to button to open menu for mobile
					$openMenu.click(function(){
						var $linkClicked = $(this);

						//close main nav drawer or search panel if open
						$("body").removeClass("campl-navigation-open");
						projectlight.$searchDrawer.removeClass("campl-search-open");

						if($linkClicked.parent().hasClass("campl-closed")){
							displayMenu("show")
						}else{
							displayMenu("hide")
						}
						return false
					});
				}
				//call function to instantiate children and title structure
				setupNavigation();
			}
		},
		hideMenu:function(){
			$openMenu = $("#menu-btn a");
			$navContainer = $(".campl-local-navigation-container");
			$openMenu.parent().removeClass("campl-open").addClass("campl-closed");
			$navContainer.css({left:-9999});
		},
		resetLocalNavigation:function(){
			//remove all sub classes
			$navContainer = $(".campl-local-navigation-container"),
			$allListItems = $navContainer.find("li");
			$allListItems.removeClass("campl-sub");
		
			//reset sub classes onto correct items
			if(projectlight.mobileLayout){
				$allListItems.has('ul').addClass("campl-sub");
			}else{
				$allListItems.not($allListItems.find("li")).has('ul').addClass("campl-sub");
			}
		}
	};
	function setupNavigation(){
		
		$navContainer = $navigation.children(".campl-local-navigation-container"),
		$topUL = $navContainer.children("ul");
		$topListItems = $topUL.children("li");
		$allListItems = $topUL.find("li");
		
		$secondLevelListitems = $topListItems.children("li");
		$allMenuLists = $topListItems.find("ul");
		$dropdownListItems = $topListItems.find("li");
		$allNavLinks = $allMenuLists.find("a");
		
		$currentPageListitem = $navigation.find(".campl-current-page");
		currentSectionNo = 0;
		
		m=$topUL.height();
		
		//need to dynamically append sub class to elements that have children
		$allListItems.has('ul').addClass("campl-sub")
		
		//this needs to be added to browsers with media queries only to prevent IE7 adding gap above items with children in desktop layout
		//for all the list items that have children append forward indicator arrow
		if(Modernizr.mq('only all')){
			$('.campl-sub').children("a").css({"position":"relative"}).append("<span class='campl-menu-indicator campl-fwd-btn'></span>")
		}
		//dynamically mark top level list items
		$topListItems.addClass("campl-top")
		

		//for each list item with a class of sub, clone the link and prepend it to the top of the nested UL beneath
		//this will act as the overview link in the top level and the UL title in the mobile navigation
		
		//for each UL walk up the DOM to find the title of the UL in the section above, prepend this link as the back button to the section before for
		//the mobile navigation
		$navigation.find(".campl-sub").each(function(){
			var $childUl = $(this).children("ul");
				$childUl.prepend('<li class="campl-title"><a href="'+ $(this).children("a").attr('href') +'">'+$(this).children("a").text()+'</a></li>');	
			if($(this).hasClass('campl-top')){
				$childUl.prepend('<li class="campl-back-link"><a href="#"><span class="campl-back-btn campl-menu-indicator"></span>Back to section home</a></li>');
			}else{
				
				$childUl.prepend('<li class="campl-back-link"><a href="#"><span class="campl-back-btn campl-menu-indicator"></span>'+ $(this).parent().children(".campl-title").children("a").html()  +'</a></li>');
			}	

		})
		
	
		//reset menu structure after title links have been appended to ensure they are always created for full mobile structure
		//desktop menu only needs to go one level deep
		$allListItems.removeClass("campl-sub");
		if(projectlight.mobileLayout){
			$allListItems.has('ul').addClass("campl-sub");
		}else{
			$allListItems.not($allListItems.find("li")).has('ul').addClass("campl-sub");
		}
		
		//declare array of links after title link has been created
		$links = $topListItems.find("a");

		//set current class to first level navigation so mobile menu can always open at least
		//one level of menu. This style makes the UL visible
		$topUL.addClass("campl-current");
		

	//hover classes not required for mobile and tablet layouts
	//hover event should only trigger from top level items not children of top level
	$topListItems.hover(
			function(){
			if(!projectlight.mobileLayout){ 
				$(this).addClass("campl-hover")
			}
		},function(){
			if(!projectlight.mobileLayout){
				$(this).removeClass("campl-hover")
			}
		});
	
		
		//Bound click event for all links inside the local navigation. 
		//handles moving forwards and backwards through pages or opening dropdown menu
		$links.click(function(e){
			var $linkClicked = $(this),
			$listItemClicked = $linkClicked.parent();
			
			if($listItemClicked.hasClass("campl-title") && Modernizr.mq('only screen and (max-width: 767px)')){
				e.preventDefault();	
			}else{
				if($listItemClicked.hasClass("campl-sub")){
					//slide mobile or tablet menu forward 
					if(projectlight.mobileLayout){
						slideMenu("forward");
						$listItemClicked.addClass("campl-current")
					}else{
						if($listItemClicked.hasClass("campl-top") && $linkClicked.hasClass("campl-clicked")){
							//toggle open navigation if top level without sub level link clicked
							closeSubNavigation();
						}else{
							//display sub menu for the desktop view for the item clicked
							showSubNavigation($linkClicked, e)
						}
					}
				e.preventDefault();	
				}else{
					if($listItemClicked.hasClass("campl-back-link")){
						slideMenu("back");
						$linkClicked.parent().parent().parent().addClass("campl-previous");
						$linkClicked.parent().parent().addClass("campl-previous");
						return false
					}
				}
			}
			
		});
		
		//ensure dropdown or sliding panels are set to the correct width if the page changes and also on first load
		$(window).resize(function(){
			setMenuWidth();
		});
		if(projectlight.mobileLayout){
			setMenuWidth();
		}
	}
	
	//sets the width of the sub menus, for either the desktop dropdown, 
	//or to ensure the mobile sliding panels stretch to fill the whole screen
	function setMenuWidth(){
		
		var widthOfMenu = 480;

		if(Modernizr.mq('only screen and (max-width: 767px)')){	
			widthOfMenu = $(window).width()

			$topUL.width(widthOfMenu);
			$allMenuLists.width(widthOfMenu).css("left",widthOfMenu);
			if($openMenu.parent().hasClass("campl-open")){
				$navContainer.css("left",-(menuPosition*widthOfMenu))
			}
			//should be adding mobile state to dom elem
			$navContainer.addClass("campl-mobile");
		}else{
			
			//this resets the mobile structure by removing all the unwanted classes 
			//so the show/hide will work for the desktop dropdown menu
			if($navContainer.hasClass("campl-mobile")){
				$openMenu.parent().removeClass("campl-open").addClass("campl-closed");
				$navContainer.find(".campl-current").removeClass("campl-current");
				$navContainer.attr("style","").removeAttr("style");
				$topUL.attr("style","").removeAttr("style");
				$allMenuLists.attr("style","").removeAttr("style")
			}
		}
	}
	//shows the desktop dropdown menus by positioning them on or off screen
	function displayMenu(actionSent){
		if(actionSent == "show"){

			//Walk up through DOM to determine nested level
			var $currentUL = $currentPageListitem.parent();
			currentSectionNo = 0;
			if($currentPageListitem.length > 0){
				if($currentPageListitem.parent().length > 0){
					//do while this is UL
					while ($currentUL[0].tagName === "UL")
					{
						$currentUL.addClass("campl-current")// this displays hidden nav sections
						if($currentUL.parent()[0].tagName === "LI" ){
							$currentUL.parent().addClass("campl-current") //need to add current to full path, UL and LI 	
						}
						$currentUL = $currentUL.parent().parent();
						currentSectionNo ++;
					}
					//set current menu position depending on which nested level the active page is on		
					menuPosition = currentSectionNo-1;
					$navContainer.children("ul").removeClass("campl-current")
				}
			}else{
				menuPosition = 0
			}

			//get current menu width
			if(Modernizr.mq('only screen and (min-width: 768px)')){
				widthOfMenu=480;
			}else{
				widthOfMenu=$(window).width();
			}

			//set left position depending which level to open menu at
			$navContainer.css({left:-(menuPosition*widthOfMenu)});
		
			$openMenu.parent().removeClass("campl-closed").addClass("campl-open");
		}else{
			if(actionSent == "hide"){
				$openMenu.parent().removeClass("campl-open").addClass("campl-closed");
				$navContainer.css({left:-9999});
				
				//need to force top container to go away. Ghost block seemed to be staying on screen even
				//though CSS should have removed it, this hack forces it to be hidden then removes the display
				//style to allow it to be controlled by the CSS again
				$navContainer.find(".campl-current").removeClass("campl-current").hide();
				$navContainer.find(':hidden').css("display", "")
				
				//reset menu back to opening position
				menuPosition = currentSectionNo-1;
			}
		}
	}
	//shows the sliding menus for the mobile navigation
	function slideMenu(directionToSlide){
		var widthOfMenu,
		currentLeftPos=$navContainer.css("left");
		currentLeftPos=parseInt(currentLeftPos.replace("px",""));
		
		if(Modernizr.mq('only screen and (min-width: 768px)')){
			widthOfMenu=480;
		}else{
			widthOfMenu=$(window).width()
		}			
		
		if(directionToSlide === "forward"){
			menuPosition++;
			$navContainer.stop().animate({left:currentLeftPos-widthOfMenu},300,function(){})
		}else{
			if(directionToSlide === "back"){
				menuPosition--;
				$navContainer.stop().animate({left:currentLeftPos+widthOfMenu},300,function(){
					$navContainer.find(".campl-previous").removeClass("campl-previous").removeClass("campl-current");
				})
			}
		}
	}
	//controls mulitple levels of dropdown navigation depending on hover and clicked classes being set
	//nb: we have altered from the original sony code by only allowing users to open one level or
	//dropdown menu in the desktop view
	function showSubNavigation(linkClicked, event){
		var $linkClicked = $(linkClicked),
		$listItemClicked = $linkClicked.parent(),
		$ListItemSiblings = $listItemClicked.siblings(),
		y;
		
		if($linkClicked.hasClass("campl-clicked")){
			$listItemClicked.removeClass("campl-hover");
			$linkClicked.removeClass("campl-clicked");
			
			//list items beneath current with hover set
			y = $listItemClicked.find(".campl-hover");
			$clickedChildren = x.find(".clicked");
			y.removeClass("campl-hover");
			$clickedChildren.removeClass("campl-clicked")
		}else{
			$listItemClicked.addClass("campl-hover");
			$linkClicked.addClass("campl-clicked");
			
			//for each of the list items siblings remove hover and clicked classes
			$ListItemSiblings.each(function(){
				var $sibling = $(this);
				if($sibling.children("a").hasClass("campl-clicked")){
					y = $sibling.find(".campl-hover");
					$clickedChildren = $sibling.find(".campl-clicked");
					$sibling.removeClass("campl-hover");
					y.removeClass("campl-hover");
					$clickedChildren.removeClass("campl-clicked")
				}
			})
		}
		event.preventDefault();
	}
	
	//close button resets all open classes and returns the navigation back to a full closed state		
	function closeSubNavigation(){
		var $hoveredListItems  =$topUL.find(".campl-hover"),
		$linksClicked = $topUL.find(".campl-clicked");
	
		$hoveredListItems.removeClass("campl-hover");
		$linksClicked.removeClass("campl-clicked");
		$secondLevelListitems.css("left",-9999)
	}

})(); //end of nav - self calling function


//DOM ready
$(function() {
	projectlight.localNav.init();
})







