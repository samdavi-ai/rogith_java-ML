FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /workspace
COPY backend/pom.xml backend/pom.xml
RUN cd backend && mvn -q -DskipTests dependency:go-offline
COPY backend/src backend/src
RUN cd backend && mvn -q -DskipTests package

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /workspace/backend/target/ewaste-assistant-0.1.0.jar /app/app.jar
COPY ml/models/ewaste.onnx /app/ml/models/ewaste.onnx
COPY ml/classes.json /app/ml/classes.json
ENV EWASTE_MODEL_PATH=/app/ml/models/ewaste.onnx
ENV EWASTE_CLASS_MAPPING_PATH=/app/ml/classes.json
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
