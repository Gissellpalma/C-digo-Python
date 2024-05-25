import mysql.connector

# Configuración de la conexión
config = {
    'user': 'root',
    'password': 'sky2003-04',
    'host': 'localhost',
    'database': 'empresa',
    'port': 3307  # Puerto especificado como 3307
}

# Crear una conexión a la base de datos
try:
    conexion = mysql.connector.connect(**config)
    
    # Verificar si la conexión es exitosa
    if conexion.is_connected():
        print("Conexión exitosa a la base de datos")

        # Crear un cursor para la inserción
        cursor = conexion.cursor()

        # Definir la consulta de inserción
        insertar_empleado = (
            "INSERT INTO empleados (Nombre, Salario, Fecha_contrato, Departamento_ID) "
            "VALUES (%s, %s, %s, %s)"
        )

        # Datos del nuevo empleado
        datos_empleado = ('Gissell Palma', 3500.00, '2024-04-24', 1)

        # Ejecutar la consulta
        cursor.execute(insertar_empleado, datos_empleado)

        # Confirmar la inserción
        conexion.commit()

        print(f"Empleado insertado, ID: {cursor.lastrowid}")

  

        # Definir la consulta de selección
        consulta = "SELECT * FROM empleados WHERE nombre = %s"
        nombre_empleado = ('Gissell Palma',)

        # Ejecutar la consulta
        cursor.execute(consulta, nombre_empleado)

        # Obtener el resultado
        resultado = cursor.fetchone()

        print("Datos del empleado:")
        print(f"ID: {resultado[0]}")
        print(f"Nombre: {resultado[1]}")
        print(f"Salario: {resultado[2]}")
        print(f"Fecha de contratación: {resultado[3]}")
        print(f"ID del departamento: {resultado[4]}")

        # Cerrar el cursor
        cursor.close()

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    if conexion.is_connected():
        conexion.close()
        print("Conexión cerrada")
