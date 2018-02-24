import shlex
import os

from . import BaseModule


class DockerModule(BaseModule):
    '''docker module
    '''

    DEFAULT_CONFIG = {
        'base_path': '.',
        'docker_bin': 'docker',
        'docker_compose_bin': 'docker-compose',
        'docker_compose_configs': None,
        'docker_compose_config_override': None,
        'docker_machine_bin': 'docker-machine',
        'data_path': None,
        'project_name': None,
        'docker_machine': None,
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
        if self.config['docker_compose_config_override'] is not None:
            override_config_file = 'docker-compose.%s.yml' % self.config['docker_compose_config_override']
            if isinstance(self.config['docker_compose_configs'], list):
                self.config['docker_compose_configs'].append(override_config_file)
            else:
                if os.path.exists(os.path.join(self.config['base_path'], 'docker-compose.override.yml')):
                    self.config['docker_compose_configs'] = ['docker-compose.yml', override_config_file, 'docker-compose.override.yml']
                else:
                    self.config['docker_compose_configs'] = ['docker-compose.yml', override_config_file]

    def get_script_env(self):
        import os

        params = {
            'project_name': shlex.quote(self.config['project_name']),
            'docker_host_system': shlex.quote(os.uname().sysname.lower()),
            'docker_host_username': shlex.quote(os.getlogin()),
            'docker_host_unix_uid': '',
            'docker_host_unix_gid': '',
            'docker_machine_env': '',
        }
        if params['docker_host_system'] in ('linux', 'darwin'):
            params.update({
                'docker_host_unix_uid': shlex.quote(str(os.getuid())),
                'docker_host_unix_gid': shlex.quote(str(os.getgid())),
            })
        if self.config['docker_machine']:
            params.update({
                'docker_machine_env': 'eval $(docker-machine env %s)' % shlex.quote(self.config['docker_machine']),
            })

        return '''
            export COMPOSE_PROJECT_NAME={project_name}
            export DOCKER_HOST_SYSTEM={docker_host_system}
            export DOCKER_HOST_USERNAME={docker_host_username}
            export DOCKER_HOST_UNIX_UID={docker_host_unix_uid}
            export DOCKER_HOST_UNIX_GID={docker_host_unix_gid}
            {docker_machine_env}
        '''.format(**params)

    def get_script(self):
        script = [super(DockerModule, self).get_script()]

        script.append(self._script_config_vars())

        script.append(self._script_function_source('install', '''
            {name}:docker-compose pull
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
                "$@"
            )
        '''.format(
            docker_env=self.get_script_env(),
            base_path=shlex.quote(self.config['base_path']),
        )))

        script.append(self._script_function_source('docker', '''
            (
                cd {base_path} && \\
                {name}:run {docker_bin} "$@"
            )
        '''.format(
            base_path=shlex.quote(self.config['base_path']),
            name=self.name,
            docker_bin=shlex.quote(self.config['docker_bin']),
        )))

        script.append(self._script_function_source('docker-compose', '''
            (
                cd {base_path} && \\
                {name}:run {docker_compose_bin} {docker_compose_configs} "$@"
            )
        '''.format(
            base_path=shlex.quote(self.config['base_path']),
            name=self.name,
            docker_compose_bin=shlex.quote(self.config['docker_compose_bin']),
            docker_compose_configs='-f %s' % ' -f '.join(map(shlex.quote, self.config['docker_compose_configs'])) \
                                    if self.config['docker_compose_configs'] else '',
        )))

        script.append(self._script_function_source('docker-machine', '''
            (
                cd {base_path} && \\
                {name}:run {docker_machine_bin} "$@"
            )
        '''.format(
            base_path=shlex.quote(self.config['base_path']),
            name=self.name,
            docker_machine_bin=shlex.quote(self.config['docker_machine_bin']),
        )))

        script.append(self._script_function_source('is_running', '''
            (
                cd {base_path} || return 1
                local pslist=$( {name}:docker-compose ps -q "$@" )
                if [ -z "$pslist" ]
                then
                    return 1
                else
                    return 0
                fi
            )
        '''.format(
            base_path=shlex.quote(self.config['base_path']),
            name=self.name,
            docker_machine_bin=shlex.quote(self.config['docker_machine_bin']),
        )))

        script.append(self._script_function_source('container_run', '''
            local options=""
            if [ "$1" == "-T" ]
            then
                options="-T $options"
                shift
            fi
            local container="${{1:-}}"
            if [ -z "$container" ]
            then
                b5:error "You need to pass the container name"
                return 1
            fi
            (
                cd {base_path} || return 1
                if {name}:is_running "$container"
                then
                    {name}:docker-compose exec $options "$@"
                else
                    {name}:docker-compose run $options --rm "$@"
                fi
            )
        '''.format(
            base_path=shlex.quote(self.config['base_path']),
            name=self.name,
        )))

        return '\n'.join(script)
