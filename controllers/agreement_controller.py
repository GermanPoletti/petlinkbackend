"""
POST	/posts/{post_id}/agreement	Iniciar acuerdo (botón "Me interesa")	User
GET	    /agreements/	            Mis acuerdos (enviados/recibidos)	User
GET	    /agreements/{id}	        Ver acuerdo + chat	User
POST	/agreements/{id}/message	Enviar mensaje	User
PATCH	/agreements/{id}/confirm	Creador: marcar como concretado	Creador
PATCH	/agreements/{id}/reject	    Creador: rechazar	Creador
DELETE	/agreements/{id}	        Cerrar chat (solo si no concretado)	Creador
"""