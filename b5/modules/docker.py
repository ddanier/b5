import shlex
import os

from . import BaseModule


class DockerModule(BaseModule):
    '''docker module
    '''

    DEFAULT_CONFIG = {
        'base_path': '.',
        'docker_compose_bin': 'docker-compose',
        'data_path': None,
        'project_name': None,
    }

    def prepare_config(self):
        self.config['base_path'] = os.path.realpath(os.path.join(
            self.state.run_path,
            self.config['base_path'],
        ))
        if self.config['data_path'] is not None:
            self.config['data_path'] = os.path.realpath(os.path.join(
                self.config['base_path'],
                self.config['data_path'],
            ))
        if self.config['project_name'] is None:
            if 'project' in self.state.config and 'key' in self.state.config['project']:
                self.config['project_name'] = self.state.config['project']['key']
            else:
                self.config['project_name'] = os.path.basename(self.state.project_path)

    def get_script_env(self):
        import os

        params = {
            'project_name': shlex.quote(self.config['project_name']),
            'docker_host_system': shlex.quote(os.uname().sysname.lower()),
            'docker_host_username': shlex.quote(os.getlogin()),
            'docker_host_unix_uid': '',
            'docker_host_unix_gid': '',
        }
        if params['docker_host_system'] in ('linux', 'darwin'):
            params.update({
                'docker_host_unix_uid': shlex.quote(str(os.getuid())),
                'docker_host_unix_gid': shlex.quote(str(os.getgid())),
            })

        return '''
            export COMPOSE_PROJECT_NAME={project_name}
            export DOCKER_HOST_SYSTEM={docker_host_system}
            export DOCKER_HOST_USERNAME={docker_host_username}
            export DOCKER_HOST_UNIX_UID={docker_host_unix_uid}
            export DOCKER_HOST_UNIX_GID={docker_host_unix_gid}
        '''.format(**params)

    def get_script(self):
        script = [super(DockerModule, self).get_script()]

        script.append(self._script_config_vars())

        script.append(self._script_function_source('install', '''
            {name}:docker-compose build
        '''.format(
            name=self.name,
        )))

        script.append(self._script_function_source('update', '''
            {name}:install
        '''.format(
            name=self.name,
        )))

        script.append(self._script_function_source('run', '''
            (
                {docker_env}
                cd {base_path} && \\
                "$@"
            )
        '''.format(
            docker_env=self.get_script_env(),
            base_path=shlex.quote(self.config['base_path']),
        )))

        script.append(self._script_function_source('docker-compose', '''
            {name}:run {docker_compose_bin} "$@"
        '''.format(
            name=self.name,
            docker_compose_bin=shlex.quote(self.config['docker_compose_bin']),
        )))

        script.append(self._script_function_source('container_run', '''
            local options=""
            if [ "$1" == "-T" ]
            then
                options="-T $options"
                shift
            fi
            {name}:docker-compose run $options --rm "$@"
        '''.format(
            name=self.name,
        )))

        return '\n'.join(script)
