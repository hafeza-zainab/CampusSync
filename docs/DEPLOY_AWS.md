# Deploying CampusSync on AWS (one EC2 instance, Docker)

> **Status: not deployed.** The `Dockerfile` in the project root was written but **has not been built or run by anyone yet** (Docker is not installed on the development machine). The packages were tested only on Windows with Python 3.14. Follow these steps, record what really happens, and only then update the "Deployment" section of [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) (see the end of this file).

## What you are deploying
One container that runs the app and the screenshot reader together (`http://<address>:8000/`). It has **no login protection beyond the demo passwords, no HTTPS and no database**. Treat it as a temporary demo, not a service.

**Read this first (security):**
- Anyone who can reach port 8000 can use the app, upload images, and call `DELETE /api/entries`. The demo passwords are public in the code. **Restrict the port to your own IP address** (step 2) and **delete the instance when you are done**.
- Do not upload real student data.
- The browser stores the app's data (localStorage), so it is per visitor; the server keeps only the extracted entries in a file inside the container (`vision/data/entries.json`), which is lost when the container is removed.

## Instance size
Measured on Windows: the server's memory peaked at **734 MB** during repeated analyses (Linux not measured). A 1 GB instance would be too small. Start with **`t3.small` (2 GB RAM)**; if it runs out of memory, use `t3.medium`. A 20 GB disk is plenty.

## Steps
**1. Launch the instance** (AWS console, EC2, *Launch instance*)
- Name `campussync-demo`; image **Amazon Linux 2023** (64-bit x86); type `t3.small`; create or choose a key pair and keep the `.pem` file.

**2. Network (security group)**
- Inbound rule: **SSH, port 22, source = My IP**.
- Inbound rule: **Custom TCP, port 8000, source = My IP** (not `0.0.0.0/0`).

**3. Connect and install Docker** (replace the key file and address)
```
ssh -i your-key.pem ec2-user@<public-ip>
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user      # then log out and back in so this takes effect
```

**4. Get the code and build the image**
```
git clone https://github.com/hafeza-zainab/CampusSync.git
cd CampusSync
docker build -t campussync .
```
*If the build fails at `pip install` because a package has no wheel for Python 3.14 on Linux,* change the first line of the `Dockerfile` to `FROM python:3.12-slim` and build again. Neither has been tested; write down which one worked.

**5. Run it**
```
docker run -d --restart unless-stopped -p 8000:8000 --name campussync campussync
docker logs -f campussync            # wait until it says "Application startup complete" (about 15-60 seconds)
```

**6. Check that it works** (from your own computer, with your IP allowed)
- Open `http://<public-ip>:8000/`: it should redirect to the app's login screen.
- Log in as `DEMO-CS-001` / `cr-demo`, open **Study Panel**, open **Import from screenshot**, upload `vision/samples/timetable_demo_new.png`: you should see the table boxes and 10 lectures.
- On the instance: `docker ps` should show the container as `healthy`.

**7. Clean up when you are finished** (to stop charges)
```
docker rm -f campussync
```
then **Terminate** the instance in the EC2 console (stopping it still charges for the disk).

## What to record (so the report can say only what is true)
Write down, with the date: the region, instance type, which base image (`3.14` or `3.12`) built, whether step 6 passed (each bullet), the time the first analysis took, and anything that failed. Send it to me, or fill in this block yourself and paste it into the "Deployment" section of `TECHNICAL_REPORT.md`:

```
Deployed on AWS EC2 on <date> in <region>, instance type <type>, Docker image built from python:<version>-slim.
Checked: login screen reachable [yes/no]; timetable_demo_new.png read, 10 lectures [yes/no]; container healthy [yes/no].
Not checked: <list>. The instance was terminated on <date>.
```
Until you have real answers, the report keeps saying: **not deployed on AWS.**
