jQuery.ajaxPrefilter(function (s) {
	if (s.crossDomain) {
		s.contents.script = false;
	}
});

(function($) {

	$(window).scroll(function(){
		// if($(window).scrollTop() < 90 && $(window).width() > 768) { 
		// 	$('#lf-header').show();
		// 	$('#header-outer').removeClass('small-nav');
		// } else {
		// 	$('#lf-header').hide();
		// 	$('#header-outer').addClass('small-nav');
		// }
	});

  $container = $('#vendor-parent, #project-parent');
  $filterSelect = $('#filter-select, #filter-select-level');

	// var mixer = mixitup('#vendor-parent');	
	if($container.length){
	  var containerEl = $('#vendor-parent, #project-parent');
	  var mixer = mixitup(containerEl, {
			animation: {
				enable: false,
			},
		  multifilter: {
	        enable: true // enable the multifilter extension for the mixer
	    }
	  });
		
		// $filterSelect.on('change', function(){
		// 	$container.mixItUp('filter', this.value);
		// });
	}

	$('#mobile-menu ul li a').click(function(ev){
		if($(this).attr('href') == '#'){
			ev.preventDefault();
			if($(this).parent().hasClass('open')){
				$(this).parent().removeClass('open');
				$(this).siblings('.sub-menu').css('display','none');				
			} else {
				$(this).parent().addClass('open');
				$(this).siblings('.sub-menu').css('display','block');				
			}
		}
	});

	$('.highlight pre').wrapInner('<code></code');
	
})(jQuery);
