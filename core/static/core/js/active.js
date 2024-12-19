$(function(){
	
	var note = $('#note'),
		// Establecemos la fecha objetivo: 20 de diciembre de 2024 a las 00:00:00
		ts = new Date(2024, 11, 20, 0, 0, 0), // Meses son indexados desde 0, por eso diciembre es 11
		newYear = false; // Ya no es un contador para año nuevo
	
	
	// Ya no necesitamos este bloque de validacion.
		
	$('#countdown').countdown({
		timestamp	: ts,
		callback	: function(days, hours, minutes, seconds){
			
			var message = "";
			
			message += days + " day" + ( days==1 ? '':'s' ) + ", ";
			message += hours + " hour" + ( hours==1 ? '':'s' ) + ", ";
			message += minutes + " minute" + ( minutes==1 ? '':'s' ) + " and ";
			message += seconds + " second" + ( seconds==1 ? '':'s' ) + " <br />";
			
			
			message += "left until launch!"; // Mensaje más apropiado para el contexto
			
			
			note.html(message);
		}
	});
	
});