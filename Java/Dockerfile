FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
COPY services ./services
ARG SERVICE
RUN test -n "$SERVICE" && mvn -B -pl "services/$SERVICE" -am package -DskipTests
FROM eclipse-temurin:21-jre
WORKDIR /app
ARG SERVICE
COPY --from=build /workspace/services/${SERVICE}/target/*.jar /app/app.jar
ENV JAVA_OPTS=""
USER 10001
EXPOSE 8080
ENTRYPOINT ["sh","-c","exec java $JAVA_OPTS -jar /app/app.jar"]
